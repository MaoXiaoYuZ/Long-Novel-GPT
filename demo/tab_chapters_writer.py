import json
import gradio as gr

from demo.gr_utils import messages2chatbot, block_diff_text, create_model_radio


def tab_chapters_writer(config):
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
            if volume_names := lngpt.get_writer().get_volume_names():
                lngpt.layers['cur_volume_name'] = volume_names[0]
            else:
                return None
        if 'cur_chapter_name' in lngpt.layers:
            del lngpt.layers['cur_chapter_name']
        return lngpt.get_writer(lngpt.layers['cur_volume_name'], None)

    with gr.Tab("生成章节") as tab:
        def create_volume_name(value):
            if not get_writer():
                return gr.Radio(choices=["请先在<生成大纲>页面中生成分卷剧情。", ], label="选择卷：", value="请先在<生成大纲>页面中生成分卷剧情。")
            available_options = lngpt.get_writer().get_volume_names()
            
            return gr.Radio(
                choices=available_options,
                label="选择卷：",
                value='',
            )

        volume_name = gr.Radio()

        chapter_name = None

        with gr.Row():
            def get_inputs_text():
                return get_writer().get_custom_system_prompt()
            
            inputs = gr.Textbox(label="大纲", lines=10, interactive=False)

            def get_output_text():
                return get_writer().json_dumps(get_writer().chapters)

            output = gr.Textbox(label="章节剧情", lines=10, interactive=False)

        def create_option(value):
            available_options = ["新建章节剧情", ]
            if get_writer().has_chat_history('init_chapters'):
                available_options.append("优化章节剧情")

            return gr.Radio(
                choices=available_options,
                label="选择你要进行的操作",
                value=value,
            )
        model = create_model_radio()        
        option = gr.Radio()

        def create_sub_option(option_value):
            if option_value == '新建章节剧情':
                return gr.Radio(["全部章节"], label="选择章节", value="")
            elif option_value == '优化章节剧情':
                return gr.Radio(["全部章节"] + get_writer().get_chapter_names(), label="选择章节", value='')

        sub_option = gr.Radio()

        def create_human_feedback(option_value):
            if option_value == '新建章节剧情':
                return gr.Textbox(value="", label="你的意见：", lines=2, placeholder="让AI知道你的意见，这在优化阶段会更有用。")
            elif option_value == '优化章节剧情':
                return gr.Textbox(value="请从情节推动不合理，剧情不符合逻辑，条理不清晰等方面进行反思。", label="你的意见：", lines=2)

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
            if sub_option == '全部章节':
                sub_option = None
            else:
                sub_option = sub_option
                    
            match option:
                case "新建章节剧情":
                    for messages in get_writer().init_chapters(human_feedback=human_feedback):
                        yield messages2chatbot(messages), generate_cost_info(messages)
                case "优化章节剧情":
                    for messages in get_writer().refine_chatpers(chapter_name=sub_option, human_feedback=human_feedback):
                        yield messages2chatbot(messages), generate_cost_info(messages)
        
        def save():
            lngpt.save(lngpt.layers['cur_volume_name'], chapter_name)
    
        def rollback(i):
            return lngpt.rollback(i, lngpt.layers['cur_volume_name'], chapter_name)  
        
        def on_roll_back():
            if FLAG['running'] == 1:
                FLAG['cancel'] = 1
                gr.Info("已暂停当前操作！")
                return

            if rollback(1):
                gr.Info("撤销成功！")
            else:
                gr.Info("已经是最早的版本了")
        
        @gr.on(triggers=[model.select, sub_option.select, human_feedback.change], inputs=[model, option, sub_option, human_feedback], outputs=[chatbot, cost_info])
        def on_cost_change(model, option, sub_option, human_feedback):
            get_writer().set_model(model)
            if option and sub_option:
                messages, cost_info = next(on_submit(option, sub_option, human_feedback))
                return messages, cost_info
            else:
                return None, None

        start_button.click(on_submit, [option, sub_option, human_feedback], [chatbot, cost_info]).success(
            save).then(
            lambda option: (get_output_text(), create_option(option), create_sub_option(option)), option, [output, option, sub_option]
        )

        rollback_button.click(on_roll_back, None, None).success(
            lambda option: (get_output_text(), create_option(''), create_sub_option(option), []), option, [output, option, sub_option, chatbot]
        )
    
    def on_select_volume_name(volume_name, evt: gr.SelectData):
        lngpt.layers['cur_volume_name'] = evt.value

    volume_name.select(on_select_volume_name, volume_name, None).then(
        lambda: (get_inputs_text(), get_output_text(), create_option(''), create_sub_option(''), []), None, [inputs, output, option, sub_option, chatbot]
        )
    
    tab.select(lambda volume_name: create_volume_name(volume_name), volume_name, volume_name).then(
        lambda : (gr.Textbox(''), gr.Textbox(''), gr.Radio([]), gr.Radio([]), []), None, [inputs, output, option, sub_option, chatbot]
        )
    
