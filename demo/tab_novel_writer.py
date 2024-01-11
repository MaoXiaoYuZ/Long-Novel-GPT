import json
import gradio as gr

from demo.gr_utils import messages2chatbot, block_diff_text

def tab_novel_writer(config):
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
        if 'cur_volume_name' not in lngpt.layers:
            return None
        if 'cur_chapter_name' not in lngpt.layers:
            cur_volume_name = lngpt.layers['cur_volume_name']
            if chapter_names := lngpt.get_writer(cur_volume_name).get_chapter_names():
                lngpt.layers['cur_chapter_name'] = chapter_names[0]
            else:
                return None
                
        return lngpt.get_writer(lngpt.layers['cur_volume_name'], lngpt.layers['cur_chapter_name'])

    with gr.Tab("生成正文") as tab:
        def create_chapter_name(value):
            if not get_writer():
                return gr.Radio(choices=["请先在<生成章节>页面中生成分章剧情。", ], label="选择章节：", value="请先在<生成章节>页面中生成分章剧情。")
            
            available_options = lngpt.get_writer(lngpt.layers['cur_volume_name']).get_chapter_names()
            
            return gr.Radio(
                choices=available_options,
                label="选择章节：",
                value='',
            )

        volume_name = None

        chapter_name = gr.Radio()

        with gr.Row():
            def get_inputs_text():
                return get_writer().get_custom_system_prompt()
            
            inputs = gr.Textbox(label="章节剧情", lines=10, interactive=False)

            def get_output_text():
                return get_writer().text

            output = gr.Textbox(label="正文", lines=10, interactive=False)

        def create_option(value):
            available_options = ["新建正文", ]
            if get_writer().has_chat_history('init_text'):
                    available_options.append("优化正文")

            return gr.Radio(
                choices=available_options,
                label="选择你要进行的操作",
                value=value,
            )
        model = gr.Radio(choices=[('gpt-3.5-turbo', 'gpt-3.5-turbo-1106'), ('gpt-4-turbo', 'gpt-4-1106-preview')], label="选择模型")
        
        option = gr.Radio()

        def create_sub_option(option_value):
            return gr.Radio(visible=False)
        
        sub_option = gr.Radio()

        def create_human_feedback(option_value):
            if option_value == '新建正文':
                return gr.Textbox(value="", label="你的意见：", lines=2, placeholder="让AI知道你的意见，这在优化阶段会更有用。")
            elif option_value == '优化正文':
                return gr.Textbox(value="请从情节推动不合理，剧情不符合逻辑，条理不清晰等方面进行反思。", label="你的意见：", lines=2)

        human_feedback = gr.Textbox()

        def on_select_option(evt: gr.SelectData):
            return create_sub_option(evt.value), create_human_feedback(evt.value)

        option.select(on_select_option, None, [sub_option, human_feedback])

        def generate_cost_info(cur_messages):
            cost = cur_messages.cost
            return gr.Markdown(f"当前操作预计消耗：{cost:.4f}$")

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
            match option:
                case "新建正文":
                    for messages in get_writer().init_text(human_feedback=human_feedback):
                        yield messages2chatbot(messages), generate_cost_info(messages)
                case "优化正文":
                    for messages in get_writer().refine_text(human_feedback=human_feedback):
                        yield messages2chatbot(messages), generate_cost_info(messages)
        
        def save():
            lngpt.save(lngpt.layers['cur_volume_name'], lngpt.layers['cur_chapter_name'])
    
        def rollback(i):
            return lngpt.rollback(i, lngpt.layers['cur_volume_name'], lngpt.layers['cur_chapter_name'])  
        
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
            get_writer().set_model(model)
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
    
    def on_select_chapter_name(chapter_name, evt: gr.SelectData):
        lngpt.layers['cur_chapter_name'] = evt.value

    chapter_name.select(on_select_chapter_name, chapter_name, None).then(
        lambda : (get_inputs_text(), get_output_text(), create_option(''), create_sub_option(''), []), None, [inputs, output, option, sub_option, chatbot]
        )
    
    tab.select(lambda chapter_name: create_chapter_name(chapter_name), chapter_name, chapter_name).then(
        lambda : (gr.Textbox(''), gr.Textbox(''), gr.Radio([]), gr.Radio([]), []), None, [inputs, output, option, sub_option, chatbot]
        )