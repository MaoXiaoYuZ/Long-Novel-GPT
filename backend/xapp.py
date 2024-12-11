from flask import Flask, request, Response, jsonify
from flask_cors import CORS
import json
import time
import random
import os

app = Flask(__name__)
CORS(app)

# 添加配置
BACKEND_HOST = os.environ.get('BACKEND_HOST', '0.0.0.0')
BACKEND_PORT = int(os.environ.get('BACKEND_PORT', 7869))

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': int(time.time())
    }), 200

# Add prompts data
PROMPTS = {
    "outline": {
        "新建章节": {
            "content": "你需要参考'小说简介'，创作一个完整的全书章节。\n按下面步骤输出：\n1.思考整个小说的故事结构\n2.创作完整的全书章节"
        },
        "扩写章节": {
            "content": "基于已有章节进行扩写和完善，使其更加详细和具体。\n请注意：\n1.保持原有故事框架\n2.添加更多细节和支线"
        },
        "润色章节": {
            "content": "对现有章节进行优化和润色。\n重点关注：\n1.故事结构的完整性\n2.情节的合理性\n3.叙事的流畅度"
        }
    },
    "plot": {
        "新建剧情": {
            "content": "根据章节创作具体剧情。\n请按以下步骤：\n1.细化场景描写\n2.丰富人物对话\n3.展现情节发展"
        },
        "扩写剧情": {
            "content": "在现有剧情基础上进行扩写。\n重点：\n1.增加细节描写\n2.深化人物刻画\n3.完善情节转折"
        }
    },
    "draft": {
        "创作正文": {
            "content": "将剧情转化为完整的小说正文。\n要求：\n1.优美的文字描写\n2.生动的场景刻画\n3.丰富的情感表达"
        },
        "修改正文": {
            "content": "对现有正文进行修改和完善。\n关注：\n1.文字表达\n2.情节连贯性\n3.人物塑造"
        }
    }
}

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


def write_chunks(chunk_list, chunk_span, writer_mode, prompt_content, x_chunk_length, y_chunk_length):
    """修改测试用的流式生成函数，添加窗口大小参数"""
    # 生成新的chunks（这里简单演示生成3个chunk）
    new_chunks = [
        ["章节1", "内容1"],
        ["章节2", "内容2"],
        ["章节3", "内容3"],
    ]
    
    # 模拟流式生成过程
    partial_texts = [""] * len(new_chunks)
    sentences = [f"这是第{i}句修改。" for i in range(1, random.randint(13, 20))]
    
    prev_chunks = None
    def delta_wrapper(chunk_list, done=False):
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


    for sentence in sentences:
        # 并行更新所有chunk的内容
        for i in range(len(new_chunks)):
            partial_texts[i] += sentence
            
        current_chunks = [
            [x, y, text] for (x, y), text in zip(new_chunks, partial_texts)
        ]
        
        yield delta_wrapper(current_chunks)

        time.sleep(0.1)  # 模拟生成延迟
    
    # 最终完成状态
    final_chunks = [
        [x, y, text] for (x, y), text in zip(new_chunks, partial_texts)
    ]
    yield delta_wrapper(final_chunks, done=True)

@app.route('/write', methods=['POST'])
def write():
    data = request.json                 
    writer_mode = data['writer_mode']
    chunk_list = data['chunk_list']
    chunk_span = data['chunk_span']
    prompt_content = data['prompt_content']
    x_chunk_length = data['x_chunk_length']
    y_chunk_length = data['y_chunk_length']
    
    def generate():
        for result in write_chunks(chunk_list, chunk_span, writer_mode, prompt_content, x_chunk_length, y_chunk_length):
            yield f"data: {json.dumps(result)}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(host=BACKEND_HOST, port=BACKEND_PORT, debug=False) 