import time
import importlib
from core.draft_writer import DraftWriter
from core.plot_writer import PlotWriter
import copy
import types

from dataclasses import asdict

def load_novel_writer(writer, setting) -> DraftWriter:
    # Reload the NovelWriter module
    importlib.reload(importlib.import_module('core.writer'))
    novel_writer_module = importlib.import_module('core.draft_writer')
    importlib.reload(novel_writer_module)
    DraftWriter = novel_writer_module.DraftWriter

    current_w_name = writer['current_w']
    current_w = writer[current_w_name]

    match current_w_name:
        case 'draft_w':
            novel_writer = DraftWriter(
                xy_pairs=list(current_w.get('xy_pairs', [['', '']])),
                xy_pairs_update_flag=list(current_w.get('xy_pairs_update_flag', [])),
                model=setting['model'],
                sub_model=setting['sub_model'],
                x_chunk_length=current_w.get('x_chunk_length', 500),
                y_chunk_length=current_w.get('y_chunk_length', 2000),
            )
        case 'outline_w':
            novel_writer = PlotWriter(
                xy_pairs=list(current_w.get('xy_pairs', [['', '']])),
                xy_pairs_update_flag=list(current_w.get('xy_pairs_update_flag', [])),
                model=setting['model'],
                sub_model=setting['sub_model'],
                x_chunk_length=current_w['x_chunk_length'],
                y_chunk_length=current_w['y_chunk_length'],
            )
        case 'chapters_w':
            novel_writer = PlotWriter(
                xy_pairs=list(current_w.get('xy_pairs', [['', '']])),
                xy_pairs_update_flag=list(current_w.get('xy_pairs_update_flag', [])),
                model=setting['model'],
                sub_model=setting['sub_model'],
                x_chunk_length=current_w.get('x_chunk_length', 200),
                y_chunk_length=current_w.get('y_chunk_length', 2000),
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

def init_chapters_w(writer):
    outline_w = writer['outline_w']
    chapters_w = writer['chapters_w']
    outline_y = "".join([e[1] for e in outline_w['xy_pairs']])
    chapters_w['xy_pairs'] = [(outline_y, '')]
    chapters_w['xy_pairs_update_flag'] = [True]

    writer["current_w"] = "chapters_w"
    return writer

def init_draft_w(writer):
    chapters_w = writer['chapters_w']
    draft_w = writer['draft_w']
    chapters_y = "".join([e[1] for e in chapters_w['xy_pairs']])
    draft_w['xy_pairs'] = [(chapters_y, '')]
    draft_w['xy_pairs_update_flag'] = [True]

    writer["current_w"] = "draft_w"
    return writer
    
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

def call_write(writer, setting, is_rewrite=False, suggestion=None):
    novel_writer = load_novel_writer(writer, setting)
    
    if is_rewrite:
        assert suggestion is not None, "rewrite需要提供suggestion"
        generator = novel_writer.rewrite_text(suggestion)
    else:
        generator = novel_writer.init_text(suggestion)    # TODO: 创作正文初稿也支持suggestion

    while True:
        # TODO: yield的返回状态信息需要结构化，暂时依靠只yield messages, update_map无更新时直接return
        try:
            chunk_list = next(generator)
            
            current_cost = 0
            apply_chunks = []
            for output, chunk in chunk_list:
                current_text = ""
                current_cost += output['response_msgs'].cost
                currency_symbol = output['response_msgs'].currency_symbol
                cost_info = f"\n(预计花费：{output['response_msgs'].cost:.4f}{output['response_msgs'].currency_symbol})"
                if 'plot2text' in output:
                    current_text += f"正在建立映射关系..." + cost_info + '\n'
                else:
                    current_text += output['text'] + cost_info + '\n'
                apply_chunks.append((asdict(chunk), 'y_chunk', current_text))
            
            yield dump_novel_writer(writer, novel_writer, apply_chunks=apply_chunks, cost=current_cost, currency_symbol=currency_symbol)

        except StopIteration as e:
            apply_chunks = []
            for output, chunk in e.value:
                apply_chunks.append((asdict(chunk), 'y_chunk', output['text']))

            new_writer = dump_novel_writer(writer, novel_writer, apply_chunks=apply_chunks)
            new_writer['prompt_outputs'] = [ele[0] for ele in e.value]
            return new_writer

def call_accept(writer, setting):
    current_w_name = writer['current_w']
    current_w = writer[current_w_name]

    novel_writer = load_novel_writer(writer, setting)
    for chunk, key, text in current_w['apply_chunks']:
        novel_writer.apply_chunk(chunk, key, text)

    generator = novel_writer.update_map()
    chunk_list = []
    while True:
        try:
            chunk_list = next(generator)
            apply_chunks = []
            for output, chunk in chunk_list:
                current_text = ""
                cost_info = f"\n(预计花费：{output['response_msgs'].cost:.4f}{output['response_msgs'].currency_symbol})"
                current_text += f"正在建立映射关系..." + cost_info + '\n'
                apply_chunks.append((asdict(chunk), 'y_chunk', current_text))

            yield dump_novel_writer(writer, novel_writer, apply_chunks=apply_chunks)
        except StopIteration as e:
            new_writer = dump_novel_writer(writer, novel_writer, apply_chunks={})
            new_writer['prompt_outputs'] = [ele[0] for ele in chunk_list]
            return new_writer
