import re
from rich.traceback import install
install(show_locals=False)

import gradio as gr
import yaml
import functools
import time
import sys
import os
import copy

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import RENDER_SAVE_LOAD_BTN, RENDER_STOP_BTN
from core.backend import call_write, call_accept, match_quote_text
from core.frontend_copy import enable_copy_js, on_copy
from core.frontend_setting import new_setting, render_setting
from core.frontend_utils import (
    title, info,
    create_progress_md, create_text_md, messages2chatbot,
    init_writer, has_accept, is_running, try_cancel, writer_y_is_empty, writer_x_is_empty,
    cancellable, process_writer_to_backend, process_writer_from_backend,
    init_chapters_w, init_draft_w
)
from core.writer_utils import KeyPointMsg

from prompts.baseprompt import clean_txt_content, load_prompt


# 读取YAML文件
with open('prompts/idea-examples.yaml', 'r', encoding='utf-8') as file:
    examples_data = yaml.safe_load(file)

# 准备示例列表
examples = [[example['idea']] for example in examples_data['examples']]

with gr.Blocks(head=enable_copy_js) as demo:
    gr.HTML(title)
    with gr.Accordion("使用指南"):
        gr.Markdown(info)

    writer_state = gr.State(init_writer('', check_empty=False))
    setting_state = gr.State(new_setting())

    if RENDER_SAVE_LOAD_BTN:
        with gr.Row():
            save_button = gr.Button("保存状态")
            load_button = gr.Button("加载状态")
            save_file_name = gr.Textbox(value='states', placeholder='输入文件名', lines=1, label=None, show_label=False, container=False)

    def save_states(save_file_name, writer, setting):
        import json
        json_file_name = save_file_name + '.json'
        with open(json_file_name, 'w', encoding='utf-8') as f:
            json.dump({
                'writer': writer,
                'setting': setting
            }, f, ensure_ascii=False, indent=2)
        gr.Info(f"状态已保存到文件：{json_file_name}")

    def load_states(save_file_name):
        import json
        json_file_name = save_file_name + '.json'
        try:
            with open(json_file_name, 'r', encoding='utf-8') as f:
                states = json.load(f)
            gr.Info(f"状态文件已加载：{json_file_name}")
            states['setting']['render_time'] = time.time()
            # 为了确保setting被渲染，选择模型是不会赋值setting_state的
            # 需要保证setting界面持有的对象和setting_state是同一个
            return states['writer'], states['setting']
        except FileNotFoundError:
            raise gr.Error(f"未找到保存的状态文件：{json_file_name}")

    idea_textbox = gr.Textbox(placeholder='用一段话描述你要写的小说，或者从下方示例中选择一个创意...', lines=2, scale=1, label=None, show_label=False, container=False, max_length=1000)
    
    gr.Examples(
        label='示例',
        examples=examples,
        inputs=[idea_textbox],
    )

    with gr.Row():    
        outline_btn = gr.Button("创作大纲", scale=1, min_width=1, interactive = True, variant='primary')
        chapters_btn = gr.Button("创作剧情", scale=1, min_width=1, interactive = False, variant='secondary')
        draft_btn = gr.Button("创作正文", scale=1, min_width=1, interactive = False, variant='secondary')
        auto_checkbox = gr.Checkbox(label='一键生成', scale=1, value=False, visible=False)  # TODO: V1.10版本 “自动”尚不完善，暂不显示

    progress_md = create_progress_md(writer_state.value)
    text_md = create_text_md(writer_state.value)

    @gr.render(inputs=writer_state)
    def create_prompt_preview(writer):
        prompt_outputs = writer['prompt_outputs'] if 'prompt_outputs' in writer else []
        with gr.Accordion("Prompt预览", open=bool(prompt_outputs)):
            pause_on_prompt_finished_checkbox = gr.Checkbox(label='允许在LLM响应完成后，预览Prompt', scale=1, value=writer['pause_on_prompt_finished_flag']) 
    
            for i, prompt_output in enumerate(prompt_outputs, 1):
                with gr.Tab(f"Prompt {i}"):
                    gr.Chatbot(messages2chatbot(prompt_output['response_msgs']), type='messages')
            if not prompt_outputs:
                gr.Markdown('当前没有可预览的Prompt。')

            continue_btn = gr.Button('继续', visible=bool(prompt_outputs), variant='primary')

        def on_pause_on_prompt_finished(value):
            if value:
                gr.Info("在LLM响应完成后，将可以预览Prompt")
            writer['pause_on_prompt_finished_flag'] = value
        
        pause_on_prompt_finished_checkbox.change(on_pause_on_prompt_finished, [pause_on_prompt_finished_checkbox])

        def on_continue(writer):
            writer['pause_flag'] = False
            writer['prompt_outputs'] = []
            return writer
        
        continue_btn.click(on_continue, writer_state, writer_state)


    with gr.Row():
        rewrite_all_button = gr.Button("开始创作", min_width=100, scale=2, variant='secondary', interactive=False)
        suggestion_dropdown = gr.Dropdown(choices=[], min_width=100, scale=2, label=None, show_label=False, container=False, allow_custom_value=False)
        quote_checkbox = gr.Checkbox(label='允许引用', min_width=100, scale=2, value=False)
        gr.Textbox('窗口大小：', container=False, text_align='right', scale=1, min_width=100)
        chunk_length_dropdown = gr.Dropdown(choices=[], min_width=80, scale=1, label=None, show_label=False, container=False, allow_custom_value=False)

    quote_md = gr.Markdown(visible=False)
    
    def on_quote_checkbox_change(writer, value):
        if writer['current_w'] == 'outline_w':
            gr.Info("大纲创作不支持引用\n考虑在剧情和正文创作中使用吧~")
            return gr.update(value=False, visible=False)
        
        if value:
            gr.Info("允许引用（右键或Ctrl+C复制你想引用的文本）")
        writer['quote_span'] = None
        writer['quoted_text'] = ''
        return gr.update(value=None, visible=False)

    quote_checkbox.change(on_quote_checkbox_change, [writer_state, quote_checkbox], [quote_md])

    def on_chunk_length_change(writer, value):
        current_w_name = writer['current_w']
        writer[current_w_name]['y_chunk_length'] = value
        return gr.update(value=value)

    chunk_length_dropdown.change(on_chunk_length_change, [writer_state, chunk_length_dropdown], [chunk_length_dropdown])

    def on_copy_handle(text, writer, setting, quote_checkbox):
        # gr.Info(f"Copy: {text}")
        text = text.strip()

        if has_accept(writer):
            gr.Info('考虑先接受或拒绝修改哦~')
            return gr.update(visible=False)

        if len(text) < 10:
            gr.Info('选中的文本太短，无法引用')
            return gr.update(visible=False)
        
        if quote_checkbox:
            quote_span, quoted_text = match_quote_text(writer, setting, text)
            if quote_span:
                writer['quote_span'] = quote_span
                writer['quoted_text'] = quoted_text
                lines = quoted_text.split('\n')
                if len(lines) > 10:
                    lines[5:-5] = ['......']
                lines = ['```', ] + lines + ['```', ]
                quoted_text = '\n'.join(["> " + e for e in lines])
                return gr.update(value=quoted_text, visible=True)
            else:
                gr.Info('未找到匹配的引用文本')

        writer['quote_span'] = None
        writer['quoted_text'] = ''
        return gr.update(visible=False)

    on_copy(on_copy_handle, [writer_state, setting_state, quote_checkbox], [quote_md])
    

    suggestion_textbox = gr.Textbox(max_length=1000, placeholder='在这里输入你的意见，或者从右上单选框选择', lines=2, scale=1, label=None, show_label=False, container=False)

    with gr.Row():    
        accept_button = gr.Button("接受", scale=1, min_width=1, variant='secondary', interactive=False)
        pause_button = gr.Button("暂停", scale=1, min_width=1, variant='secondary', visible=RENDER_STOP_BTN)
        stop_button = gr.Button("取消", scale=1, min_width=1, variant='secondary')
        flash_button = gr.Button("刷新", scale=1, min_width=1, variant='secondary')

    def flash_interface(writer):
        current_w_name = writer['current_w']

        can_accept_flag = has_accept(writer) and not is_running(writer)
        can_write_flag = not writer_x_is_empty(writer, current_w_name) and not can_accept_flag

        match current_w_name:
            case 'outline_w':
                rewrite_all_button = gr.update(value='开始创作', variant='primary' if can_write_flag else 'secondary', interactive=can_write_flag)
            case 'chapters_w':
                rewrite_all_button = gr.update(value='开始创作', variant='primary' if can_write_flag else 'secondary', interactive=can_write_flag)
            case 'draft_w':
                rewrite_all_button = gr.update(value='开始创作', variant='primary' if can_write_flag else 'secondary', interactive=can_write_flag)

        accept_button = gr.update(variant='primary' if can_accept_flag else 'secondary', interactive=can_accept_flag)
        
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

        pause_button = gr.update(
            value="继续" if writer['pause_flag'] else "暂停",
            variant='secondary',
        )

        suggestion_choices = writer['suggestions'][current_w_name]
        # suggestion_choices = ['自动', ] + writer['suggestions'][current_w_name]  # TODO: V1.10版本 “自动”尚不完善，暂不显示
        if writer_y_is_empty(writer, current_w_name):
            suggestion_dropdown = gr.update(choices=suggestion_choices, value=suggestion_choices[0])
        else:
            suggestion_dropdown = gr.update(choices=suggestion_choices,)

        chunk_length_choices = writer['chunk_length'][current_w_name]
        if cur_chunk_length := writer[current_w_name].get('y_chunk_length', None):
            chunk_length_dropdown = gr.update(choices=chunk_length_choices, value=cur_chunk_length)
        else:
            chunk_length_dropdown = gr.update(choices=chunk_length_choices, value=chunk_length_choices[0])

        return (
            create_text_md(writer),
            create_progress_md(writer),
            rewrite_all_button,
            accept_button,
            outline_btn,
            chapters_btn,
            draft_btn,
            pause_button,
            suggestion_dropdown,
            chunk_length_dropdown
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
            draft_btn,
            pause_button,
            suggestion_dropdown,
            chunk_length_dropdown
        ]
    )
    
    flash_button.click(**flash_event)
    if RENDER_SAVE_LOAD_BTN:
        save_button.click(save_states, inputs=[save_file_name, writer_state, setting_state], outputs=[])
        load_button.click(load_states, inputs=[save_file_name], outputs=[writer_state, setting_state]).success(**flash_event)
    # stop_write_long_novel_button.click(on_cancel, inputs=[writer_state])
    stop_button.click(try_cancel, inputs=[writer_state]).success(**flash_event).success(lambda :gr.update(), None, writer_state)
    # TODO: stop_btn对writer_state的更新没有起效

    @cancellable
    def _on_write_all(writer, setting, auto_write=False, suggestion=None):
        current_w_name = writer['current_w']
           
        if writer_x_is_empty(writer, current_w_name):
            gr.Info('请先输入需要创作的内容！')
            return
        
        writer['prompt_outputs'].clear()

        if writer['quote_span']:
            quote_span, quoted_text = match_quote_text(writer, setting, writer['quoted_text'])
            if quote_span != writer['quote_span'] or quoted_text != writer['quoted_text']:
                raise gr.Error('引用文本不存在！')

        generator = call_write(process_writer_to_backend(writer), setting, auto_write, suggestion)

        new_writer = None
        while True:
            try:
                kp_msg = next(generator)
                if isinstance(kp_msg, KeyPointMsg):
                    # TODO: 由于KeyPointMsg的设计问题，这里的逻辑比较复杂，后续可以考虑优化
                    if kp_msg.is_prompt() and kp_msg.is_finished() and writer['pause_on_prompt_finished_flag']:
                        gr.Info('LLM响应完成，可以预览Prompt')  
                        writer['pause_flag'] = True
                        if new_writer is None: continue
                    elif kp_msg.is_title(): # TODO: 标题节点还未实现finish逻辑
                        # if new_writer is not None:
                        #     # 说明这是一个关键节点，进行保存
                        #     process_writer_from_backend(writer, new_writer)
                        #     yield create_text_md(writer), writer
                        #     gr.Info(f'已自动保存进度')
                        continue
                        # 关键节点保存的逻辑比较复杂，有bug，之后版本考虑提供
                    else:
                        continue
                else:
                    new_writer = kp_msg
                
                if writer['pause_flag']:
                    writer['prompt_outputs'] = copy.deepcopy(new_writer['prompt_outputs'])  
                    # 将prompt_outputs传递到writer_state中，使得暂停时能显示prompt, 需要序列化，否则writer会不断更新，导致prompt不断渲染
                    yield create_text_md(new_writer), writer

                    while writer['pause_flag'] and not writer['cancel_flag']:
                        time.sleep(0.1)
                else:
                    yield create_text_md(new_writer), gr.update()
            except StopIteration as e:
                # 这里处理最终状态
                process_writer_from_backend(writer, e.value)
                yield create_text_md(writer), writer
                if has_accept(writer):
                    gr.Info('创作完成！点击接受按钮接受修改。')
                else:
                    gr.Info('本次创作没有任何更改。')  # 通常因为审阅意见认为无需更改
                return
        
    def on_auto_write_all(writer, setting, auto_write):
        if auto_write:
            yield from _on_write_all(writer, setting, True)
        else:
            pass
            # suggestion = writer['suggestions'][writer['current_w']][0]
            # yield from _on_write_all(writer, setting, False, suggestion)

    writer_all_events = dict(
            fn=on_auto_write_all,
            queue=True,
            inputs=[writer_state, setting_state, auto_checkbox],
            outputs=[text_md, writer_state],
            concurrency_limit=10
    )

    def on_init_outline(idea, writer):
        if not idea.strip():
            gr.Info("先输入小说简介或从示例中选择一个")
            return gr.update()
        new_writer = init_writer(idea)
        writer.update({
            k:v for k, v in new_writer.items() if k in ['current_w', 'outline_w', 'prompt_outputs']
        })
        return writer
    
    outline_btn.click(on_init_outline, inputs=[idea_textbox, writer_state], outputs=[writer_state]).success(**writer_all_events).then(**flash_event)
    chapters_btn.click(lambda writer: init_chapters_w(writer), inputs=[writer_state], outputs=[writer_state]).success(**writer_all_events).then(**flash_event)
    draft_btn.click(lambda writer: init_draft_w(writer), inputs=[writer_state], outputs=[writer_state]).success(**writer_all_events).then(**flash_event)

    def on_select_suggestion(writer, setting, choice):
        if choice == '自动':
            return gr.update(value=choice, visible=False)

        current_w_name = writer['current_w']
        dirname = writer['suggestions_dirname'][current_w_name]
        suggestion = clean_txt_content(load_prompt(dirname, choice))
        if suggestion.startswith("user:\n"):
            suggestion = suggestion[len("user:\n"):]
        
        return gr.update(value=suggestion, visible=True)
    
    suggestion_dropdown.change(on_select_suggestion, inputs=[writer_state, setting_state, suggestion_dropdown], outputs=[suggestion_textbox])

    def on_write_all(writer, setting, suggestion):
        if not suggestion.strip():
            gr.Info('需要输入创作意见！')
            return
        yield from _on_write_all(writer, setting, False, suggestion)
        
    rewrite_all_button.click(
            on_write_all,
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
        
        new_writer = call_accept(process_writer_to_backend(writer), setting)
        process_writer_from_backend(writer, new_writer)
        yield create_text_md(writer), writer
    
    accept_button.click(fn=on_accept_write, inputs=[writer_state, setting_state], outputs=[text_md, writer_state]).then(**flash_event)

    def toggle_pause(writer):
        if not is_running(writer):
            gr.Info('当前没有正在进行的操作')
            return gr.update()
        
        writer['pause_flag'] = not writer['pause_flag']
        # gr.Info('已' + ('暂停' if writer['pause_flag'] else '继续') + '操作')
        return gr.update(value="暂停" if not writer['pause_flag'] else "继续")

    pause_button.click(
        toggle_pause,
        inputs=[writer_state],
        outputs=[pause_button]
    )

    @gr.render(inputs=setting_state)
    def _render_setting(setting):
        return render_setting(setting, setting_state)


demo.queue()
demo.launch(server_name="0.0.0.0", server_port=7860)
#demo.launch()


