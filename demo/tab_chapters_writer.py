import json
import time
import gradio as gr

from demo.gr_utils import enable_change_output, messages2chatbot, block_diff_text, create_model_radio, generate_cost_info, create_selected_text


def tab_chapters_writer(config):
    lngpt = config['lngpt']

    def get_writer():
        nonlocal lngpt
        lngpt = config['lngpt']
        if not lngpt:
            return None
        return lngpt.get_writer('chapters')

    with gr.Tab("生成章节") as tab:
        with gr.Row():
            def get_inputs_text():
                return get_writer().get_input_context()
            
            inputs = gr.Textbox(label="大纲", lines=10, interactive=False)

            def get_output_text():
                return get_writer().get_output()

            output = gr.Textbox(label="章节剧情", lines=10, interactive=True)

        def create_option(value):
            available_options = ["新建章节剧情", ]
            if get_writer().get_chapter_names():
                available_options.append("重写章节剧情")

            return gr.Radio(
                choices=available_options,
                label="选择你要进行的操作",
                value=value,
            )
        model = create_model_radio()        
        option = gr.Radio()

        def create_sub_option(option_value):
            return gr.Radio(visible=False)
        
        sub_option = gr.Radio()

        selected_output_text = create_selected_text(output)
        enable_change_output(get_writer, output)

        def create_human_feedback(option_value):
            if option_value == '新建章节剧情':
                value = f"创建第{len(get_writer().get_chapter_names()) + 1}章剧情：..."
                return gr.Textbox(value=value, label="你的意见：", lines=2, placeholder="让AI知道你的意见，这在优化阶段会更有用。")
            elif option_value == '重写章节剧情':
                return gr.Textbox(value="", label="你的意见：", lines=2)
            elif option_value == '讨论':
                return gr.Textbox(value="不要急于得出结论，让我们先一步一步的思考", label="你的意见：", lines=2)

        human_feedback = gr.Textbox()

        def on_select_option(evt: gr.SelectData):
            return create_sub_option(evt.value), create_human_feedback(evt.value)

        option.select(on_select_option, None, [sub_option, human_feedback])

        cost_info = gr.Markdown('当前操作预计消耗：0$')
        start_button = gr.Button("开始创作", variant='primary')

        with gr.Row():
            resubmit_button = gr.Button("重来")
            cancel_button = gr.Button("取消")
            rollback_button = gr.Button("回退")

            resubmit_button.click(lambda: config.update(resubmit_flag=True), [], [])

        chatbot = gr.Chatbot()
        def check_running(func):
            def wrapper(option, sub_option, human_feedback, selected_output_text):
                try:
                    config['resubmit_flag'] = True
                    while config['resubmit_flag']:
                        config['resubmit_flag'] = False

                        for ret in func(option, sub_option, human_feedback, selected_output_text):
                            yield ret
                            
                            if config['resubmit_flag']:
                                break
                            
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    raise gr.Error(str(e))
            return wrapper
        
        @check_running
        def on_submit(option, sub_option, human_feedback, selected_output_text):
            selected_output_text = selected_output_text.strip()
                    
            match option:
                case '讨论':
                    for messages in get_writer().discuss(human_feedback):
                        yield messages2chatbot(messages), generate_cost_info(messages), gr.update()
                case "新建章节剧情":
                    for messages in get_writer().init_chapters(human_feedback=human_feedback, selected_text=selected_output_text):
                        yield messages2chatbot(messages), generate_cost_info(messages),  gr.update(value="新建章节剧情...")
                case "重写章节剧情":
                    for i, messages in enumerate(get_writer().rewrite_chatpers(human_feedback=human_feedback, selected_text=selected_output_text)):
                        yield messages2chatbot(messages), generate_cost_info(messages),  gr.update(value="重写章节剧情...")
                        if i == 0 and not selected_output_text:
                            raise gr.Error('请先在正文栏中选定要重写的部分！')
        
        def save():
            lngpt.save('chapters')
    
        def rollback(i):
            return lngpt.rollback(i, 'chapters')  
        
        def on_roll_back(start_button):
            if start_button != "开始创作":
                raise Exception('先取消正在进行的操作再回退！')

            if rollback(1):
                gr.Info("撤销成功！")
            else:
                gr.Info("已经是最早的版本了")
        
        @gr.on(triggers=[model.select, option.select, human_feedback.change], inputs=[model, option, sub_option, human_feedback, selected_output_text], outputs=[chatbot, cost_info])
        def on_cost_change(model, option, sub_option, human_feedback, selected_output_text):
            if model: get_writer().set_model(model)
            if option:
                try:
                    messages, cost_info, _ = next(on_submit(option, sub_option, human_feedback, selected_output_text))
                except Exception as e:
                    gr.Info(str(e))
                    return gr.update(), gr.update()
                return messages, cost_info
            else:
                return gr.update(), gr.update()

        event_submit = start_button.click(lambda: gr.update(interactive=False), [], start_button).then(
            on_submit, [option, sub_option, human_feedback, selected_output_text], [chatbot, cost_info, start_button])

        fn_enable_submit = dict(fn=lambda: gr.update(interactive=True, value='开始创作'), inputs=None, outputs=[start_button, ])
        
        event_submit.success(
            save).then(
            lambda option: (get_output_text(), create_option(''), create_sub_option(option), gr.update(value='')), option, [output, option, sub_option, selected_output_text]
        ).then(**fn_enable_submit)

        cancel_button.click(fn=lambda: gr.update(interactive=True), inputs=None, outputs=[start_button, ], cancels=[event_submit, ]).then(**fn_enable_submit)

        rollback_button.click(on_roll_back, start_button, None).success(
            lambda option: (get_output_text(), create_option(''), create_sub_option(option), []), option, [output, option, sub_option, chatbot]
        )
    
    def on_select_tab():
        if get_writer():
            return get_inputs_text(), get_output_text(), create_option(''), create_sub_option(''), []
        else:
            gr.Info("请先选择小说名！")
            return gr.Textbox(''), gr.Textbox(''), gr.Radio([]), gr.Radio([]), []
    
    tab.select(on_select_tab, None, [inputs, output, option, sub_option, chatbot])
    
