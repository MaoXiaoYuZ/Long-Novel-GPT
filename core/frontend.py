from rich.console import Console
from rich.traceback import install
install(show_locals=True)
console = Console()

import gradio as gr
import yaml

import time
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.backend import call_write, call_accept, call_write_long_novel, init_chapters_w, init_draft_w
from core.frontend_setting import new_setting, render_setting
from llm_api import ModelConfig, wenxin_model_config, doubao_model_config, test_stream_chat

from core.utils import create_comparison_table

import functools

def init_writer(idea):
    outline_w = dict(
        current_cost=0,
        total_cost=0,
        currency_symbol='￥',
        xy_pairs=[(idea, '')],
        xy_pairs_update_flag=[False],   # outline 不进行映射
        x_chunk_length=10_000,   # 由于不进行映射，chunk设为无穷大
        y_chunk_length=10_000,
        apply_chunks={},
    )
    chapters_w = dict(
        current_cost=0,
        total_cost=0,
        currency_symbol='￥',
        xy_pairs=[('', '')],
        apply_chunks={},
    )
    draft_w = dict(
        current_cost=0,
        total_cost=0,
        currency_symbol='￥',
        xy_pairs=[('', '')],
        apply_chunks={},
    )
    return dict(
        current_w='outline_w',
        outline_w=outline_w,
        chapters_w=chapters_w,
        draft_w=draft_w,
        running_flag=False,
        cancel_flag=False,  # 用于取消正在进行的操作
        progress={},
        prompt_outputs=[],  # 这一行未注释时，将在gradio界面中显示prompt_outputs
    )

def can_cancel(writer):
    if writer['running_flag'] and not writer['cancel_flag']:
        return True
    else:
        current_w = writer[writer['current_w']]
        if current_w['apply_chunks']:
            return True
        else:
            return False

def cancellable(func):
    @functools.wraps(func)
    def wrapper(writer, *args, **kwargs):
        if can_cancel(writer): 
            if writer['running_flag']:
                gr.Warning('另一个操作正在进行中，请等待其完成或取消！')
                return
            elif wrapper.__name__ != "on_accept_write":
                gr.Warning('有正在等待接受的文本，点击接受或取消！')
                return
        
        writer['running_flag'] = True
        writer['cancel_flag'] = False
        
        generator = func(writer, *args, **kwargs)
        
        try:
            while True:
                if writer['cancel_flag']:
                    gr.Info('操作已取消！')
                    return
                
                try:
                    result = next(generator)
                    if isinstance(result, tuple) and (writer_dict := next((item for item in result if isinstance(item, dict) and 'running_flag' in item), None)):
                        writer = writer_dict
                    yield result
                except StopIteration as e:
                    return e.value
                except Exception as e:
                    console.print_exception(show_locals=True)
                    raise gr.Error(f'操作过程中发生错误：{e}')
        finally:
            writer['running_flag'] = False
    
    return wrapper

def try_cancel(writer):
    if not can_cancel(writer):
        gr.Info('当前没有正在进行的操作或待接受的文本')
        return
    
    current_w = writer[writer['current_w']]
    if not writer['running_flag'] and current_w['apply_chunks']:    # 优先取消正在进行的操作
        current_w['apply_chunks'].clear()
        gr.Info('已取消待接受的文本')
        return

    writer['cancel_flag'] = True
    
    start_time = time.time()
    while writer['running_flag'] and time.time() - start_time < 3:
        time.sleep(0.1)
    
    if writer['running_flag']:
        gr.Warning('取消操作超时，可能需要刷新页面')
    
    writer['cancel_flag'] = False
    
def writer_y_is_empty(writer, w_name):
    xy_pairs = writer[w_name]['xy_pairs']
    return sum(len(e[1]) for e in xy_pairs) == 0


# 读取YAML文件
with open('prompts/idea-examples.yaml', 'r', encoding='utf-8') as file:
    examples_data = yaml.safe_load(file)

# 准备示例列表
examples = [[example['idea']] for example in examples_data['examples']]

title = """
<div style="text-align: center; padding: 10px 20px;">
    <h1 style="margin: 0 0 5px 0;">🖋️ Long-Novel-GPT 1.8</h1>
    <p style="margin: 0;"><em>让每个人都能轻松创作自己心目中的小说</em></p>
</div>
"""

info = \
"""1. 当前Demo支持GPT、Claude、文心、豆包等模型，并且已经配置了API-Key，默认模型为GPT4o，最大线程数为5。
2. 可以选中**示例**中的任意一个提纲，然后点击**创作大纲**来初始化大纲。
3. 初始化后，不断点击**扩写**按钮，可以不断扩写大纲，直到满意为止。
4. 创建完大纲后，点击**创作剧情**按钮，可以创作剧情，之后重复以上流程。
5. 在模型响应**完成后**，在**Prompt预览**中可以查看当前的Prompt和模型的响应。
6. 如果遇到任何无法解决的问题，请点击**刷新**按钮。
7. 如果问题还是无法解决，请刷新浏览器页面，这会导致丢失所有数据，请手动备份重要文本。
"""

with gr.Blocks() as demo:
    gr.HTML(title)
    with gr.Accordion("使用指南"):
        gr.Markdown(info)

    writer_state = gr.State(init_writer(''))
    setting_state = gr.State(new_setting())

    # with gr.Row():
    #     save_button = gr.Button("保存状态")
    #     load_button = gr.Button("加载状态")

    def save_states(writer, pair, setting):
        import json
        with open('states.json', 'w', encoding='utf-8') as f:
            json.dump({
                'writer': writer,
                'pair': pair,
                'setting': setting
            }, f, ensure_ascii=False, indent=2)
        gr.Info("状态已保存")

    def load_states():
        import json
        try:
            with open('states.json', 'r', encoding='utf-8') as f:
                states = json.load(f)
            gr.Info("状态已加载")
            return states['writer'], states['pair'], states['setting']
        except FileNotFoundError:
            gr.Error("未找到保存的状态文件")

    def create_progress_md(writer):
        progress_md = ""
        if 'progress' in writer and writer['progress']:
            progress = writer['progress']
            progress_md = ""
            
            # 使用集合来去重并保持顺序
            titles = []
            subtitles = {}
            current_op_ij = (float('inf'), float('inf'))
            for opi, op in enumerate(progress['ops']):
                if op['title'] not in titles:
                    titles.append(op['title'])
                if op['title'] not in subtitles:
                    subtitles[op['title']] = []
                if op['subtitle'] not in subtitles[op['title']]:
                    subtitles[op['title']].append(op['subtitle'])
                
                if opi == progress['cur_op_i']:
                    current_op_ij = (len(titles), len(subtitles[op['title']]))
            
            for i, title in enumerate(titles, 1):
                progress_md += f"## {['一', '二', '三', '四', '五', '六', '七', '八', '九', '十'][i-1]}、{title}\n"
                for j, subtitle in enumerate(subtitles[title], 1):
                    if i < current_op_ij[0] or (i == current_op_ij[0] and j < current_op_ij[1]):
                        progress_md += f"### {j}、{subtitle} ✓\n"
                    elif i == current_op_ij[0] and j == current_op_ij[1]:
                        progress_md += f"### {j}、{subtitle} {'.' * (int(time.time()) % 4)}\n"
                    else:
                        progress_md += f"### {j}、{subtitle}\n"
                
                progress_md += "\n"
            
            progress_md += "---\n"
            # TODO: 考虑只放当前进度

        return gr.Markdown(progress_md)
    
    def create_text_md(writer):
        current_w_name = writer['current_w']
        current_w = writer[current_w_name]
        apply_chunks = current_w['apply_chunks']

        match current_w_name:
            case 'draft_w':
                column_names = ['剧情', '正文', '修正稿']
            case 'outline_w':
                column_names = ['创意', '大纲', '修正稿']
            case 'chapters_w':
                column_names = ['大纲', '剧情', '修正稿']
            case _:
                raise Exception('当前状态不正确')

        if apply_chunks:
            table = [[*e, ''] for e in current_w['xy_pairs']]
            occupied_rows = [False] * len(table)
            for chunk, key, text in apply_chunks:
                assert key == 'y_chunk'
                pair_span = chunk['pair_span']
                if any(occupied_rows[pair_span[0]:pair_span[1]]):
                    raise Exception('apply_chunks中存在重叠的pair_span')
                occupied_rows[pair_span[0]:pair_span[1]] = [True] * (pair_span[1] - pair_span[0])
                table[pair_span[0]:pair_span[1]] = [[chunk['x_chunk'], chunk['y_chunk'], text], ] + [None] * (pair_span[1] - pair_span[0] - 1)
            table = [e for e in table if e is not None]
            if not any(e[1] for e in table):
                column_names = column_names[:2]
                table = [[e[0], e[2]] for e in table]
            md = create_comparison_table(table, column_names=column_names)
        else:
            xy_pairs = current_w['xy_pairs']
            if len(xy_pairs) == 1 and (not xy_pairs[0][0].strip() or not xy_pairs[0][1].strip()):
                tip_x = '从下方示例中选择一个创意用于创作小说。'
                tip_y = '选择创意后，点击创作大纲。更详细的操作请参考使用指南。'
                if not xy_pairs[0][0].strip():
                    xy_pairs = [[tip_x, tip_y]]
                else:
                    xy_pairs = [[xy_pairs[0][0], tip_y]]

            md = create_comparison_table(xy_pairs, column_names=column_names[:2])
        return gr.Markdown(md, height='600px')

    idea_textbox = gr.Textbox(placeholder='用一段话描述你要写的小说，或者从下方示例中选择一个创意...', lines=1, scale=1, label=None, show_label=False, container=False, max_length=20)
    
    gr.Examples(
        label='示例',
        examples=examples,
        inputs=[idea_textbox],
    )

    # with gr.Row():    
    #     write_long_novel_button = gr.Button("一键生成全书", scale=3, min_width=1, variant='primary')
    #     stop_write_long_novel_button = gr.Button("暂停", scale=1, min_width=1, variant='secondary')

    with gr.Row():    
        outline_btn = gr.Button("创作大纲", scale=1, min_width=1, interactive = True, variant='primary')
        chapters_btn = gr.Button("创作剧情", scale=1, min_width=1, interactive = False, variant='secondary')
        draft_btn = gr.Button("创作正文", scale=1, min_width=1, interactive = False, variant='secondary')

    progress_md = create_progress_md(writer_state.value)
    text_md = create_text_md(writer_state.value)

    @gr.render(inputs=writer_state)
    def create_prompt_preview(writer):
        prompt_outputs = writer['prompt_outputs'] if 'prompt_outputs' in writer else []
        with gr.Accordion("Prompt预览", open=not prompt_outputs):
            for i, prompt_output in enumerate(prompt_outputs, 1):
                with gr.Tab(f"Prompt {i}"):
                    gr.Chatbot(prompt_output['response_msgs'], type='messages')
     
    with gr.Row():
        rewrite_all_button = gr.Button("扩写", scale=1, min_width=1, variant='secondary', interactive=False)
        suggestion_textbox = gr.Textbox(placeholder='对文本进行润色', lines=1, scale=1, label=None, show_label=False, container=False)

    with gr.Row():    
        accept_button = gr.Button("接受", scale=1, min_width=1, variant='secondary', interactive=False)
        stop_button = gr.Button("取消", scale=1, min_width=1, variant='secondary')
        flash_button = gr.Button("刷新", scale=1, min_width=1, variant='secondary')


    def flash_interface(writer):
        current_w_name = writer['current_w']
        current_w = writer[current_w_name]

        can_accept_flag = can_cancel(writer) and not writer['running_flag']

        match current_w_name:
            case 'outline_w':
                rewrite_all_button = gr.update(value='扩写全部大纲', variant='secondary', interactive=not can_accept_flag)
            case 'chapters_w':
                rewrite_all_button = gr.update(value='扩写全部剧情', variant='secondary', interactive=not can_accept_flag)
            case 'draft_w':
                rewrite_all_button = gr.update(value='扩写全部正文', variant='secondary', interactive=not can_accept_flag)

        accept_button = gr.update(interactive=can_accept_flag, variant='primary' if can_accept_flag else 'secondary')
        
        # 更新 chapters_btn 和 draft_btn 的 interactive 状态
        outline_btn = gr.update(
            variant='primary' if current_w_name == 'outline_w' else 'secondary'
            )
        chapters_btn = gr.update(
            interactive=not writer_y_is_empty(writer, 'outline_w'),
            variant='primary' if current_w_name == 'chapters_w' else 'secondary'
        )
        draft_btn = gr.update(
            interactive=not writer_y_is_empty(writer, 'chapters_w'),
            variant='primary' if current_w_name == 'draft_w' else 'secondary'
        )

        return (
            create_text_md(writer),
            create_progress_md(writer),
            rewrite_all_button,
            accept_button,
            outline_btn,
            chapters_btn,
            draft_btn
        )

    # 更新 flash_event 字典以包含新的输出
    flash_event = dict(
        fn=flash_interface, 
        inputs=[writer_state], 
        outputs=[
            text_md,
            progress_md,
            rewrite_all_button,
            accept_button,
            outline_btn,
            chapters_btn,
            draft_btn
        ]
    )
    
    flash_button.click(**flash_event)
    # save_button.click(save_states, inputs=[writer_state, pair_state, setting_state], outputs=[])
    # load_button.click(load_states, outputs=[writer_state, pair_state, setting_state]).success(**flash_event)
    # stop_write_long_novel_button.click(on_cancel, inputs=[writer_state])
    stop_button.click(try_cancel, inputs=[writer_state]).success(**flash_event) 
    
    @cancellable
    def on_write_long_novel(writer, setting, idea):
        if not idea.strip():
            raise gr.Error('请先用一段话描述你要写的小说！')
        
        if writer['outline_w']['xy_pairs'][0][0] == idea:
            gr.Info('继续生成小说！')
        else:
            writer = init_writer(idea)  # 如果writer引用发生了改变，那么应该返回新的writer，反之一样。
            yield create_text_md(writer), create_progress_md(writer), writer

        generator = call_write_long_novel(writer, setting)
        
        new_writer = next(generator)
        op_id = new_writer['progress']['cur_op_i']

        try:
            while True:
                try:
                    new_writer = next(generator)
                    if new_writer['progress']['cur_op_i'] != op_id: # 说明这是一个发生了重要节点变化，保存writer
                        op_id = new_writer['progress']['cur_op_i']
                        yield create_text_md(new_writer), create_progress_md(new_writer), new_writer
                        writer = new_writer  # 一方面是为了将本函数的writer和外部的writer_state同步，另一方面是为了成功cancel
                    else:
                        yield create_text_md(new_writer), create_progress_md(new_writer), gr.update()
                except StopIteration as e:
                    final_writer = e.value
                    yield create_text_md(final_writer), create_progress_md(final_writer), final_writer
                    gr.Info('全书生成完成！')
                    return
        except Exception as e:
            gr.Info(str(e))
            console.print_exception(show_locals=True)
            return

    # write_long_novel_button.click(
    #     on_write_long_novel,
    #     queue=True,
    #     inputs=[writer_state, setting_state, idea_textbox],
    #     outputs=[text_md, progress_md, writer_state],
    #     concurrency_limit=10
    # ).success(**flash_event)

    @cancellable
    def _on_write_all(writer, setting, is_rewrite=False, suggestion=None):
        current_w_name = writer['current_w']
        current_w = writer[current_w_name]
        
        if is_rewrite:
            if not current_w['xy_pairs'] or (len(current_w['xy_pairs']) == 1 and not current_w['xy_pairs'][0][1].strip()):
                gr.Info('请先进行创作！')
                yield gr.update(), writer
                return
        else:
            if not current_w['xy_pairs'] or (len(current_w['xy_pairs']) == 1 and not current_w['xy_pairs'][0][0].strip()):
                gr.Info('请先输入需要创作的内容！')
                yield gr.update(), writer
                return
        
        if current_w['apply_chunks']:
            gr.Info('已自动删除未接受的修改！')
            current_w['apply_chunks'].clear()
        
        if is_rewrite:
            match writer['current_w']:
                case 'outline_w':
                    suggestion = '考虑将其某些行的剧情展开为多行的剧情。先思考哪些行可以展开。'
                case 'chapters_w':
                    suggestion = '考虑将其中某些行的剧情展开为多行的剧情。先思考哪些行可以展开。'
                case 'draft_w':
                    suggestion = '创作的是正文，而不是剧情，需要像一个小说家那样去描写这个故事。'
        else:
            match writer['current_w']:
                case 'outline_w':
                    suggestion = '构思全书的大致剧情，并将其以一个故事的形式写下来，10-20行左右。'
                case 'chapters_w':
                    suggestion = '考虑将其中某些行的剧情展开为多行的剧情。先思考哪些行可以展开。'
                case 'draft_w':
                    suggestion = '创作的是正文，而不是剧情，需要像一个小说家那样去描写这个故事。'

        generator = call_write(writer, setting, is_rewrite, suggestion)

        while True:
            try:
                new_writer = next(generator)
                yield create_text_md(new_writer), gr.update()
            except StopIteration as e:
                # 这里处理最终状态
                final_writer = e.value
                yield create_text_md(final_writer), final_writer
                gr.Info('创作完成！点击接受按钮接受修改。')
                return
        
    def on_write_all(writer, setting):
        yield from _on_write_all(writer, setting, False, None)

    writer_all_events = dict(
            fn=on_write_all,
            queue=True,
            inputs=[writer_state, setting_state],
            outputs=[text_md, writer_state],
            concurrency_limit=10
    )
    
    outline_btn.click(lambda idea: init_writer(idea), inputs=[idea_textbox], outputs=[writer_state]).success(**writer_all_events).then(**flash_event)
    chapters_btn.click(lambda writer: init_chapters_w(writer), inputs=[writer_state], outputs=[writer_state]).success(**writer_all_events).then(**flash_event)
    draft_btn.click(lambda writer: init_draft_w(writer), inputs=[writer_state], outputs=[writer_state]).success(**writer_all_events).then(**flash_event)

    def on_rewrite_all(writer, setting, suggestion):
        yield from _on_write_all(writer, setting, True, suggestion)
        
    rewrite_all_button.click(
            on_rewrite_all,
            queue=True,
            inputs=[writer_state, setting_state, suggestion_textbox],
            outputs=[text_md, writer_state],
            concurrency_limit=10
        ).then(**flash_event)    


    @cancellable
    def on_accept_write(writer, setting):
        current_w_name = writer['current_w']
        current_w = writer[current_w_name]
        
        if not current_w['apply_chunks']:
            raise gr.Error('请先进行创作！')
        
        generator = call_accept(writer, setting)

        while True:
            try:
                new_writer = next(generator)
                yield create_text_md(new_writer), gr.update()
            except StopIteration as e:
                new_writer = e.value
                yield create_text_md(new_writer), new_writer
                return
            
    accept_button.click(fn=on_accept_write, inputs=[writer_state, setting_state], outputs=[text_md, writer_state]).then(**flash_event)

    @gr.render(inputs=setting_state)
    def _render_setting(setting):
        return render_setting(setting, setting_state)


demo.queue()
demo.launch(server_name="0.0.0.0", server_port=7860)
#demo.launch()


