import json
import gradio as gr

from demo.gr_utils import messages2chatbot, block_diff_text, create_model_radio


def tab_outline_writer(config):
    lngpt = config['lngpt']
    FLAG = {
        'running': 0,
        'cancel': 0,
    }

    def get_writer():
        nonlocal lngpt
        lngpt = config['lngpt']
        if not lngpt:
            return None
        return lngpt.get_writer('outline')

    with gr.Tab("生成大纲") as tab:
        with gr.Row():
            with gr.Column():
                def get_inputs_text():
                    return get_writer().get_input_context()

                inputs = gr.Textbox(label="这是一部什么样的小说？", lines=10, interactive=False)

            def get_output_text():
                return get_writer().get_output()

            output = gr.Textbox(label="生成的小说大纲", lines=10, interactive=True)


        def create_option(value):
            available_options = ["讨论", "创作小说设定", ]
            return gr.Radio(
                choices=available_options,
                label="选择你要进行的操作",
                value='',
            )
        model = create_model_radio()        
        option = gr.Radio()

        def create_sub_option(option_value):
            return gr.Radio(["全部章节"], label="选择章节", value="", visible=False)

        sub_option = gr.Radio()

        def create_human_feedback(option_value):
            human_feedback_string = ''
            writer = get_writer()
            if option_value == '创作小说设定':
                if writer.outline:
                    human_feedback_string = writer.get_config("refine_outline_setting")
                else:
                    human_feedback_string = writer.get_config("init_outline_setting")
            elif option_value == '讨论':
                human_feedback_string = "不要急于得出结论，让我们先一步一步的思考"

            return gr.Textbox(value=human_feedback_string, label="你的意见：", lines=2, placeholder="让AI知道你的意见。")
        
        human_feedback = gr.Textbox()

        def on_select_option(evt: gr.SelectData):
            return create_sub_option(evt.value), create_human_feedback(evt.value)

        option.select(on_select_option, None, [sub_option, human_feedback])

        def generate_cost_info(cur_messages):
            cost = cur_messages.cost
            currency_symbol = cur_messages.currency_symbol
            return gr.Markdown(f"当前操作预计消耗：{cost:.4f}{currency_symbol}")

        cost_info = gr.Markdown('当前操作预计消耗：0$')
        start_button = gr.Button("开始")
        rollback_button = gr.Button("撤销")

        chatbot = gr.Chatbot()

        def check_running(func):
            def wrapper(*args, **kwargs):
                if FLAG['running'] == 1:
                    gr.Info("当前有操作正在进行，请稍后再试！")
                    return

                FLAG['running'] = 1
                try:
                    for ret in func(*args, **kwargs):
                        if FLAG['cancel']:
                            FLAG['cancel'] = 0
                            break
                        yield ret
                except Exception as e:
                    raise gr.Error(e)
                finally:
                    FLAG['running'] = 0
            return wrapper
        
        @check_running
        def on_submit(option, sub_option, human_feedback):
            if not option:
                gr.Info("请先选择操作！")
                return
              
            match option:
                case '讨论':
                    for messages in get_writer().discuss(human_feedback):
                        yield messages2chatbot(messages), generate_cost_info(messages)
                case '创作小说设定':
                    for messages in get_writer().init_outline_setting(human_feedback=human_feedback):
                        yield messages2chatbot(messages), generate_cost_info(messages)
        
        def save():
            lngpt.save('outline')
    
        def rollback(i):
            return lngpt.rollback(i, 'outline')  
        
        def on_roll_back():
            if FLAG['running'] == 1:
                FLAG['cancel'] = 1
                gr.Info("已暂停当前操作！")
                return

            if rollback(1):
                gr.Info("撤销成功！")
            else:
                gr.Info("已经是最早的版本了")
        
        @gr.on(triggers=[model.select, option.select, human_feedback.change], inputs=[model, option, sub_option, human_feedback], outputs=[chatbot, cost_info])
        def on_cost_change(model, option, sub_option, human_feedback):
            if model: 
                get_writer().set_model(model)
            else:
                return None, None
            if option:
                messages, cost_info = next(on_submit(option, sub_option, human_feedback))
                return messages, cost_info
            else:
                return None, None

        start_button.click(on_submit, [option, sub_option, human_feedback], [chatbot, cost_info]).success(
            save).then(
            lambda option: (get_output_text(), create_option(''), create_sub_option(option)), option, [output, option, sub_option]
        )

        rollback_button.click(on_roll_back, None, None).success(
            lambda option: (get_output_text(), create_option(''), create_sub_option(option), []), option, [output, option, sub_option, chatbot]
        )
    
    def on_select_tab():
        if get_writer():
            return get_inputs_text(), get_output_text(), create_option(''), create_sub_option(''), []
        else:
            gr.Info("请先选择小说名！")
            return gr.Textbox(''), gr.Textbox(''), gr.Radio([]), gr.Radio([]), []
    
    tab.select(on_select_tab, None, [inputs, output, option, sub_option, chatbot])
    