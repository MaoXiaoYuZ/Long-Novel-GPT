import json
import time

from flask import Flask, request, Response, jsonify
from flask_cors import CORS
app = Flask(__name__)
CORS(app)

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import API_SETTINGS
from llm_api import ModelConfig
from prompts.baseprompt import clean_txt_content, load_prompt

from core.writer_utils import KeyPointMsg
from core.draft_writer import DraftWriter
from core.plot_writer import PlotWriter
from core.outline_writer import OutlineWriter


# 添加配置
BACKEND_HOST = os.environ.get('BACKEND_HOST', '0.0.0.0')
BACKEND_PORT = int(os.environ.get('BACKEND_PORT', 7860))


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': int(time.time())
    }), 200


def load_novel_writer(writer_mode, chunk_list, x_chunk_length, y_chunk_length, model_provider) -> DraftWriter:
    kwargs = dict(
        xy_pairs=chunk_list,
        model=get_model_config_from_settings(model_provider, 'main'),
        sub_model=get_model_config_from_settings(model_provider, 'sub'),
    )

    kwargs['x_chunk_length'] = x_chunk_length
    kwargs['y_chunk_length'] = y_chunk_length

    match writer_mode:
        case 'draft':
            novel_writer = DraftWriter(**kwargs)
        case 'outline':
            novel_writer = OutlineWriter(**kwargs)
        case 'chapters' | 'plot':
            novel_writer = PlotWriter(**kwargs)
        case _:
            raise ValueError(f"unknown writer: {writer_mode}")
            
    return novel_writer


def get_model_config_from_settings(model_provider, model_type):
    provider_config = API_SETTINGS[model_provider]
    
    if model_provider == 'doubao':
        if model_type == 'main':
            model_config = {**provider_config, 'model': provider_config['default_model'], 'endpoint_id': provider_config['main_endpoint_id']}
        elif model_type == 'sub':
            model_config = {**provider_config, 'model': provider_config['default_sub_model'], 'endpoint_id': provider_config['sub_endpoint_id']}
    else:
        model_config = {**provider_config, 'model': provider_config['default_model']}

    return ModelConfig(**model_config)


prompt_names = dict(
    outline = ['新建大纲', '扩写大纲', '润色大纲'],
    plot = ['新建剧情', '扩写剧情', '润色剧情'],
    draft = ['新建正文', '扩写正文', '润色正文'],
)

prompt_dirname = dict(
    outline = 'prompts/创作大纲',
    plot = 'prompts/创作剧情',
    draft = 'prompts/创作正文',
)


PROMPTS = {}
for type_name, dirname in prompt_dirname.items():
    PROMPTS[type_name] = {'prompt_names': prompt_names[type_name]}
    for name in prompt_names[type_name]:
        content = clean_txt_content(load_prompt(dirname, name))
        if content.startswith("user:\n"):
            content = content[len("user:\n"):]
        PROMPTS[type_name][name] = {'content': content}


@app.route('/prompts', methods=['GET'])
def get_prompts():
    return jsonify(PROMPTS)

def get_delta_chunks(prev_chunks, curr_chunks):
    """Calculate delta between previous and current chunks"""
    if not prev_chunks or len(prev_chunks) != len(curr_chunks):
        return "init", curr_chunks
    
    # Check if all strings in current chunks start with their corresponding previous strings
    is_delta = True
    for prev_chunk, curr_chunk in zip(prev_chunks, curr_chunks):
        if len(prev_chunk) != len(curr_chunk):
            is_delta = False
            break
        for prev_str, curr_str in zip(prev_chunk, curr_chunk):
            if not curr_str.startswith(prev_str):
                is_delta = False
                break
        if not is_delta:
            break
    
    if not is_delta:
        return "init", curr_chunks
    
    # Calculate deltas
    delta_chunks = []
    for prev_chunk, curr_chunk in zip(prev_chunks, curr_chunks):
        delta_chunk = []
        for prev_str, curr_str in zip(prev_chunk, curr_chunk):
            delta_str = curr_str[len(prev_str):]
            delta_chunk.append(delta_str)
        delta_chunks.append(delta_chunk)
    
    return "delta", delta_chunks


def call_write(writer_mode, chunk_list, chunk_span, prompt_content, x_chunk_length, y_chunk_length, model_provider):
    # 输入的chunk_list中每个chunk需要加上换行，除了最后一个chunk（因为是从页面中各个chunk传来的）
    chunk_list = [[e.strip() + ('\n' if e.strip() and rowi != len(chunk_list)-1 else '') for e in row] for rowi, row in enumerate(chunk_list)]

    prev_chunks = None
    def delta_wrapper(chunk_list, done=False):
        # 返回的chunk_list中每个chunk需要去掉换行
        chunk_list = [[e.strip() for e in row] for row in chunk_list]

        nonlocal prev_chunks
        if prev_chunks is None:
            prev_chunks = chunk_list
            return {
                "done": done,
                "chunk_type": "init",
                "chunk_list": chunk_list
            }
        else:
            chunk_type, new_chunks = get_delta_chunks(prev_chunks, chunk_list)
            prev_chunks = chunk_list
            return {
                "done": done,
                "chunk_type": chunk_type,
                "chunk_list": new_chunks
            }
        
    novel_writer = load_novel_writer(writer_mode, chunk_list, x_chunk_length, y_chunk_length, model_provider)
    

    # 进行初始的区块划分
    target_chunk = novel_writer.get_chunk(pair_span=chunk_span)
    new_target_chunk = novel_writer.map_text_wo_llm(target_chunk)
    novel_writer.apply_chunks([target_chunk], [new_target_chunk])
    chunk_span = novel_writer.get_chunk_pair_span(new_target_chunk)
    init_novel_writer = load_novel_writer(writer_mode, list(novel_writer.xy_pairs), x_chunk_length, y_chunk_length, model_provider)
    
    # TODO: writer.write 应该保证无论什么prompt，都能够同时适应y为空和y有值地情况
    # 换句话说，就是虽然可以单列出一个“新建正文”，但用扩写正文也能实现同样的效果。
    generator = novel_writer.write(prompt_content, pair_span=chunk_span) 
    
    prompt_outputs = []
    last_yield_time = time.time()  # Initialize the last yield time

    for kp_msg in generator:
        if isinstance(kp_msg, KeyPointMsg):
            # 如果要支持关键节点保存，需要计算一个编辑上的更改，然后在这里yield writer
            continue
        else:
            chunk_list = kp_msg

        current_cost = 0
        data_chunks = []
        prompt_outputs.clear()
        for output, chunk in chunk_list:
            prompt_outputs.append(output)
            current_text = ""
            current_cost += output['response_msgs'].cost
            currency_symbol = output['response_msgs'].currency_symbol
            cost_info = f"\n(预计花费：{output['response_msgs'].cost:.4f}{output['response_msgs'].currency_symbol})"
            if 'plot2text' in output:
                current_text += f"正在建立映射关系..." + cost_info + '\n'
            else:
                current_text = output['text']
                # current_text += output['text'] + cost_info + '\n'
            data_chunks.append((chunk.x_chunk, chunk.y_chunk, current_text))
        
        current_time = time.time()
        if current_time - last_yield_time >= 0.2:  # Check if 0.2 seconds have passed
            yield delta_wrapper(data_chunks, done=False)
            last_yield_time = current_time  # Update the last yield time

    # 这里是计算出一个编辑上的更改，方便前端显示，后续diff功能将不由writer提供，因为这是为了显示的要求
    data_chunks = []
    for chunk, key, value in init_novel_writer.diff_to(novel_writer, pair_span=chunk_span):
        data_chunks.append((chunk.x_chunk, chunk.y_chunk, value))

    yield delta_wrapper(data_chunks, done=True)


@app.route('/write', methods=['POST'])
def write():
    data = request.json
    writer_mode = data['writer_mode']
    chunk_list = data['chunk_list']
    chunk_span = data['chunk_span']
    prompt_content = data['prompt_content']
    x_chunk_length = data['x_chunk_length']
    y_chunk_length = data['y_chunk_length']
    model_provider = data['model_provider']
    
    def generate():
        try:
            for result in call_write(writer_mode, list(chunk_list), chunk_span, prompt_content, x_chunk_length, y_chunk_length, model_provider):
                yield f"data: {json.dumps(result)}\n\n"
        except Exception as e:
            error_msg = f"创作出错：\n{str(e)}"
            error_chunk_list = [[*e[:2], error_msg] for e in chunk_list[chunk_span[0]:chunk_span[1]]]
            
            error_data = {
                "done": True,
                "chunk_type": "init",
                "chunk_list": error_chunk_list
            }
            yield f"data: {json.dumps(error_data)}\n\n"
            return
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(host=BACKEND_HOST, port=BACKEND_PORT, debug=False) 