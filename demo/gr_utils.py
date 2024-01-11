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
