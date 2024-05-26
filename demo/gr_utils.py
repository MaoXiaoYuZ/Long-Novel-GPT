import gradio as gr

def parse_user_id(request):
    return request.request.cookies['_gid']

def messages2chatbot(messages):
    chatbot = []
    for msg in messages:
        role, content = msg["role"], msg["content"]
        if role == "system" or role == "user":
            chatbot.append([content, None])
        else:
            chatbot[-1][1] = content

    return chatbot

def block_diff_text():
    with gr.Row():
        texta = gr.Textbox(label="修改前", lines=4)
        textb = gr.Textbox(label="修改后", lines=4)
    with gr.Row():
        cancel = gr.Button("放弃修改")
        accept = gr.Button("接受修改")
    # difftext = gr.HighlightedText(
    #     label="Diff",
    #     combine_adjacent=True,
    #     show_legend=True,
    #     color_map={"+": "green", "-": "red"})
    
    # @gr.on(triggers=[texta.change, textb.change], inputs=[texta, textb], outputs=difftext)
    # def diff_texts(text1, text2):
    #     d = Differ()
    #     return [
    #         (token[2:], token[0] if token[0] != " " else None)
    #         for token in d.compare(text1, text2)
    #     ]
    
    return texta, textb, cancel, accept

def create_model_radio():
    return gr.Radio(choices=[
        ('gpt-3.5-turbo', 'gpt-3.5-turbo-1106'), 
        ('gpt-4-turbo', 'gpt-4-1106-preview'),
        ('chatgpt（暂不支持）', 'chatgpt-4'),
        ('文心3.5', 'ERNIE-Bot'),
        ('文心4.0', 'ERNIE-Bot-4')
        ], label="选择模型")

def create_selected_text(output):
    def on_select_output(evt: gr.SelectData): 
        #gr.Info(f"You selected {evt.value} at {evt.index} from {evt.target}")
        return gr.Textbox(evt.value, visible=True)
    
    def on_focus_output(): 
        #gr.Info("You focus!")
        return gr.Textbox('', visible=False)
    
    selected_output_text = gr.Textbox(label="选中的文本", interactive=False, visible=False)
    output.select(on_select_output, None, selected_output_text)
    output.focus(on_focus_output, None, selected_output_text)

    return selected_output_text

def enable_change_output(get_writer, output):
    def on_blur_output(output): 
        try:
            get_writer().set_output(output)
            return gr.Textbox()
        except Exception as e:
            gr.Info(str(e))
            return get_writer().get_output()
    output.blur(on_blur_output, output, output)

def generate_cost_info(cur_messages):
    if hasattr(cur_messages, 'cost'):
        cost = cur_messages.cost
        currency_symbol = cur_messages.currency_symbol
        return gr.Markdown(f"当前操作预计消耗：{cost:.4f}{currency_symbol}", visible=True)
    else:
        return gr.Markdown(visible=False)