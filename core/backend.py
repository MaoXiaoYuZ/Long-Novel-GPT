import time
import importlib
from core.draft_writer import DraftWriter
from core.plot_writer import PlotWriter
from core.outline_writer import OutlineWriter
from core.writer_utils import KeyPointMsg
import copy
import types

from dataclasses import asdict

def load_novel_writer(writer, setting) -> DraftWriter:
    current_w_name = writer['current_w']
    current_w = writer[current_w_name]

    match current_w_name:
        case 'draft_w':
            novel_writer = DraftWriter(
                xy_pairs=list(current_w.get('xy_pairs', [['', '']])),
                xy_pairs_update_flag=list(current_w.get('xy_pairs_update_flag', [])),
                model=setting['model'],
                sub_model=setting['sub_model'],
            )
        case 'outline_w':
            novel_writer = OutlineWriter(
                xy_pairs=list(current_w.get('xy_pairs', [['', '']])),
                xy_pairs_update_flag=list(current_w.get('xy_pairs_update_flag', [])),
                model=setting['model'],
                sub_model=setting['sub_model'],
            )
        case 'chapters_w':
            novel_writer = PlotWriter(
                xy_pairs=list(current_w.get('xy_pairs', [['', '']])),
                xy_pairs_update_flag=list(current_w.get('xy_pairs_update_flag', [])),
                model=setting['model'],
                sub_model=setting['sub_model'],
            )
        case _:
            raise ValueError(f"unknown writer: {current_w_name}")
            
    return novel_writer

def dump_novel_writer(writer, novel_writer, apply_chunks={}, cost=0, currency_symbol='￥'):
    new_writer = copy.deepcopy(writer)  # TODO: dump从设计角度上来说，不应该更改原有的writer，但是在此处copy可能更耗时

    current_w_name = new_writer['current_w']
    current_w = new_writer[current_w_name]

    # if current_w_name == 'draft_w':
    #     assert isinstance(novel_writer, DraftWriter), "draft_w需要传入DraftWriter"

    current_w['xy_pairs'] = list(novel_writer.xy_pairs)
    current_w['xy_pairs_update_flag'] = list(novel_writer.xy_pairs_update_flag)
        
    current_w['current_cost'] = cost
    current_w['currency_symbol'] = currency_symbol
    #current_w['total_cost'] += current_w['current_cost']

    current_w['apply_chunks'] = apply_chunks
    
    return new_writer
    
def call_write_long_novel(writer, setting):
    writer = copy.deepcopy(writer)
    progress = writer['progress']
    
    if not progress or True:
        progress = dict(
            cur_op_i = progress['cur_op_i'] if progress else 0,
            ops = [
                {
                    'before_eval': 'writer["current_w"] = "outline_w"',
                    'eval': 'call_write(writer, setting, False, "构思全书的大致剧情，并将其以一个故事的形式写下来，只写大致情节。")',
                    'title': '创作大纲',
                    'subtitle': '生成大纲'
                },
                {
                    'eval': 'call_accept(writer, setting)',
                },
                {
                    'eval': 'call_write(writer, setting, True, "对整个情节进行重写，使其更加有故事性。")',
                    'title': '创作大纲',
                    'subtitle': '润色大纲',
                },
                {
                    'eval': 'call_accept(writer, setting)',
                },
                # 下面是创作剧情
                {
                    'before_eval': 'init_chapters_w(writer)',
                    'eval': 'call_write(writer, setting, False, "丰富其中的剧情细节。")',
                    'title': '创作剧情',
                    'subtitle': '生成剧情'
                },
                {
                    'eval': 'call_accept(writer, setting)',
                },
                {
                    'eval': 'call_write(writer, setting, True, "对情节进行重写，使其有更多的剧情细节，同时更加有具有故事性。")',
                    'title': '创作剧情',
                    'subtitle': '扩充剧情',
                },
                {
                    'eval': 'call_accept(writer, setting)',
                },
                # 下面是创作正文
                {
                    'before_eval': 'init_draft_w(writer)',
                    'eval': 'call_write(writer, setting, False, "创作的是正文，而不是剧情，需要像一个小说家那样去描写这个故事。")',
                    'title': '创作正文',
                    'subtitle': '生成正文'
                },
                {
                    'eval': 'call_accept(writer, setting)',
                },
                {
                    'eval': 'call_write(writer, setting, True, "润色正文")',
                    'title': '创作正文',
                    'subtitle': '润色正文'
                },
                {
                    'eval': 'call_accept(writer, setting)',
                }
            ]
        )

        # TODO: 考虑在init_plot时就给到上下文，类似rewrite_plot
        
        title, subtitle = '', ''
        for op in progress['ops']:
            if 'title' not in op:
                op['title'], op['subtitle'] = title, subtitle
            else:
                title, subtitle = op['title'], op['subtitle']

    
    writer['progress'] = progress
    yield writer

    while progress['cur_op_i'] < len(progress['ops']):
        current_op = progress['ops'][progress['cur_op_i']]
        if 'before_eval' in current_op:
            exec(current_op['before_eval'])
        writer = yield from eval(current_op['eval'])
        progress = writer['progress']
        
        progress['cur_op_i'] += 1
        yield writer    # 当cur_op_i有更新时，也就标志着yield的是一个“稳定版本”的writer_state

    return writer

# 这是后端函数，接受前端writer_state的copy做为输入
# 返回的是修改后的writer_state，注意yield的值一般被用于前端展示执行的过程和进度
# 只有return值才会被前端考虑用于writer_state的更新
def call_write(writer, setting, auto_write=False, suggestion=None):
    novel_writer = load_novel_writer(writer, setting)

    # TODO: 临时代码，后续会移除
    for _ in novel_writer.update_map(): break   # 执行生成器直到第一个yield
    current_w = writer[writer['current_w']]
    current_w['xy_pairs'] = list(novel_writer.xy_pairs)
    current_w['xy_pairs_update_flag'] = list(novel_writer.xy_pairs_update_flag)
    
    if auto_write:
        generator = novel_writer.auto_write()
    else:
        generator = novel_writer.write(suggestion) 
    
    prompt_outputs = []
    for kp_msg in generator:
        if isinstance(kp_msg, KeyPointMsg):
            # 如果要支持关键节点保存，需要计算一个编辑上的更改，然后在这里yield writer
            yield kp_msg
            continue
        else:
            chunk_list = kp_msg

        current_cost = 0
        apply_chunks = []
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
                current_text += output['text'] + cost_info + '\n'
            apply_chunks.append((asdict(chunk), 'y_chunk', current_text))
        
        new_writer = dump_novel_writer(writer, novel_writer, apply_chunks=apply_chunks, cost=current_cost, currency_symbol=currency_symbol)
        new_writer['prompt_outputs'] = prompt_outputs
        yield new_writer

    # 这里是计算出一个编辑上的更改，方便前端显示，后续diff功能将不由writer提供，因为这是为了显示的要求
    apply_chunks = []
    for chunk, key, value in load_novel_writer(writer, setting).diff_to(novel_writer):
        apply_chunks.append((asdict(chunk), key, value))
    writer[writer['current_w']]['apply_chunks'] = apply_chunks
    writer['prompt_outputs'] = prompt_outputs
    return writer

def call_accept(writer, setting):
    current_w_name = writer['current_w']
    current_w = writer[current_w_name]

    novel_writer = load_novel_writer(writer, setting)
    for chunk, key, text in current_w['apply_chunks']:
        novel_writer.apply_chunk(chunk, key, text)

    generator = novel_writer.update_map()
    chunk_list = []
    prompt_outputs = []
    for kp_msg in generator:
        if isinstance(kp_msg, KeyPointMsg):
            continue
        else:
            chunk_list = kp_msg
        apply_chunks = []
        prompt_outputs.clear()
        for output, chunk in chunk_list:
            prompt_outputs.append(output)
            current_text = ""
            cost_info = f"\n(预计花费：{output['response_msgs'].cost:.4f}{output['response_msgs'].currency_symbol})"
            current_text += f"正在建立映射关系..." + cost_info + '\n'
            apply_chunks.append((asdict(chunk), 'y_chunk', current_text))

        new_writer = dump_novel_writer(writer, novel_writer, apply_chunks=apply_chunks)
        new_writer['prompt_outputs'] = prompt_outputs
        yield new_writer
    
    writer = dump_novel_writer(writer, novel_writer)
    writer['prompt_outputs'] = prompt_outputs
    return writer
