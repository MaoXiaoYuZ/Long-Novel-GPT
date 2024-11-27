import gradio as gr

enable_copy_js = """
<script>
document.addEventListener('copy', function(e) {
    // 获取选中的文本
    var selectedText = window.getSelection().toString();
    if(selectedText) {
        // 直接触发 gradio 组件的更新
        const textbox = document.getElementById('copy_textbox');
        if(textbox) {
            textbox.querySelector('textarea').value = selectedText;
            // 触发 change 事件以更新 Gradio 状态
            textbox.querySelector('textarea').dispatchEvent(new Event('input', { bubbles: true }));
        }
    }
});
</script>
"""

def on_copy(fn, inputs, outputs):
    copy_textbox = gr.Textbox(elem_id="copy_textbox", visible=False)
    return copy_textbox.change(fn, [copy_textbox] + inputs, outputs)


# with gr.Blocks(head=enable_copy_js) as demo:
#     gr.Markdown("Hello\nTest Copy")
#     copy_textbox = gr.Textbox(elem_id="copy_textbox", visible=False)

#     def copy_handle(text):
#         gr.Info(text)
    
#     copy_textbox.change(copy_handle, copy_textbox)
    
# demo.launch()