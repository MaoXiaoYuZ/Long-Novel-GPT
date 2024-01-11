import os
import json
import gradio as gr

from llm_api.openai_api import set_gpt_api_config, test_gpt_api, openai_config
from demo.wrapper_for_demo import Long_Novel_GPT_Wrapper

def tab_setting(config):
    
    with gr.Tab("设置") as tab:
        with gr.Blocks():
            api_key = gr.Textbox()
            base_url = gr.Textbox()
            with gr.Row():
                test_button = gr.Button('测试OpenAI API')
                report = gr.Textbox(label='测试结果', value='', interactive=False)
            
            def on_click_test_button(api_key, base_url):
                set_gpt_api_config(api_key=api_key, base_url=base_url)
                return test_gpt_api()
            
            test_button.click(on_click_test_button, [api_key, base_url], report)
        
        with gr.Blocks():
            chat_context_limit = gr.Number()
            def on_change_chat_context_limit(chat_context_limit):
                config['chat_context_limit'] = int(chat_context_limit)
            chat_context_limit.change(on_change_chat_context_limit, chat_context_limit, None)
    
    def init_tab():
        api_key = gr.Textbox(label='openai api_key', value=openai_config['api_key'], lines=1, placeholder='这里输入openai api key', interactive=True)
        base_url = gr.Textbox(label='openai base_url', value=openai_config['base_url'], lines=1, placeholder='这里输入openai base url', interactive=True)
        chat_context_limit = gr.Number(label='chat_context_limit', info='llm api的最大上下文长度，超过此长度会进行压缩', value=config['chat_context_limit'], interactive=True)

        return api_key, base_url, chat_context_limit

    tab.select(init_tab, None, [api_key, base_url, chat_context_limit])