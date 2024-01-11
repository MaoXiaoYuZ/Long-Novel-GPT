import os
import gradio as gr

from demo.wrapper_for_demo import Long_Novel_GPT_Wrapper

def tab_main_page(config):
    def get_available_input_options():
        input_options = []
        if not os.path.exists("output"):
            os.makedirs("output")
        for name in os.listdir("output"):
            if os.path.isdir(os.path.join("output", name)):
                input_options.append(name)
        return input_options

    def create_option(e):
        return gr.Radio(label='选择操作', choices=['新建小说', '加载小说'], value=e)

    def create_input_options(e=''):
        input_options = get_available_input_options()
        return gr.Radio(label='加载已有小说名', choices=input_options, value=e)

    with gr.Tab("选择小说名") as tab:
        option = create_option('')
        input_options = gr.Radio(label='', choices=[])
        inputs = gr.Textbox(label='', value='', lines=1, interactive=False)
        details = gr.Textbox(label="这是一部什么样的小说？", lines=4, placeholder="可以选择在这里输入更多细节", interactive=True)
        submit = gr.Button("开始创作")
    
    def on_select_option(evt: gr.SelectData):
        if evt.value == '加载小说':
            return create_input_options(''), gr.Textbox(label='', value='', interactive=False)
        else:
            return gr.Radio(label='', choices=[]), gr.Textbox(label="输入新的小说名", value='', interactive=True)


    option.select(on_select_option, None, [input_options, inputs])
    
    def get_lngpt_by_inputs(inputs):
        path = f"output/{inputs}"
        lngpt = Long_Novel_GPT_Wrapper(path)
        lngpt.writer_config = config
        if not os.path.exists(path):
            os.makedirs(path)
            return lngpt
        else:
            lngpt.load_checkpoints()
            return lngpt
    
    def on_select_input_options(evt: gr.SelectData):
        if evt.value:
            inputs = evt.value
            lngpt = get_lngpt_by_inputs(inputs)
            details = lngpt.get_writer().get_custom_system_prompt()
            return gr.Textbox(interactive=False), gr.Textbox(details)

    input_options.select(on_select_input_options, None, [inputs, details])

    def on_submit(option, input_options, inputs, details):
        path = f"output/{inputs}"

        if option == '新建小说':
            if not inputs:
                gr.Info("请输入小说名")
                #return None, None, None, None
            exists_options = get_available_input_options()
            if inputs in exists_options:
                gr.Info(f"小说名：{inputs}已经存在，请重新输入")
                #return None, None, None, None
            lngpt = get_lngpt_by_inputs(inputs)
            if inputs not in details:
                details = f"{inputs}\n{details}"
            lngpt.get_writer().set_custom_system_prompt(details)
            lngpt.save()
        elif option == '加载小说':
            inputs = input_options
            lngpt = get_lngpt_by_inputs(inputs)
            lngpt.load_checkpoints()
            lngpt.get_writer().set_custom_system_prompt(details)
            lngpt.save()
        else:
            gr.Info("请选择操作")
            #return None, None, None, None
        
        config['lngpt'] = lngpt
        config['novel_name'] = inputs
        config['novel_details'] = details

        gr.Info(f"已经加载小说：{inputs}，接下来在<生成大纲>页面中生成小说大纲!")

        #return None, None, None, None
        

    submit.click(on_submit, [option, input_options, inputs, details], None)
    #tab.select(create_input_options, input_options, input_options)