import os
import json
import gradio as gr

from llm_api.openai_api import set_gpt_api_config, test_gpt_api, openai_config
from llm_api.chatgpt_api import set_chatgpt_api_config, test_chatgpt_api, chatgpt_config
from llm_api.baidu_api import set_wenxin_api_config, test_wenxin_api, baidu_config
from demo.wrapper_for_demo import Long_Novel_GPT_Wrapper

def tab_setting(config):
    
    with gr.Tab("设置") as tab:
        with gr.Blocks():
            openai_api_key = gr.Textbox()
            openai_base_url = gr.Textbox()
            with gr.Row():
                test_button = gr.Button('测试OpenAI API')
                report = gr.Textbox(label='测试结果', value='', interactive=False)
            
            def on_click_test_button(api_key, base_url):
                set_gpt_api_config(api_key=api_key, base_url=base_url)
                return test_gpt_api()
            
            test_button.click(on_click_test_button, [openai_api_key, openai_base_url], report)

        with gr.Blocks():
            chatgpt_base_url = gr.Textbox()
            with gr.Row():
                test_button = gr.Button('测试ChatGPT API')
                report = gr.Textbox(label='测试结果', value='', interactive=False)
            
            def on_click_test_button(base_url):
                set_chatgpt_api_config(base_url=base_url)
                return test_chatgpt_api()
            
            test_button.click(on_click_test_button, [chatgpt_base_url], report)


        with gr.Blocks():
            baidu_access_key = gr.Textbox()
            baidu_secret_key = gr.Textbox()
            with gr.Row():
                test_button = gr.Button('测试文心一言API')
                report = gr.Textbox(label='测试结果', value='', interactive=False)
            
            def on_click_test_button(access_key, secret_key):
                set_wenxin_api_config(access_key=access_key, secret_key=secret_key)
                return test_wenxin_api()
            
            test_button.click(on_click_test_button, [baidu_access_key, baidu_secret_key], report)

        with gr.Blocks():
            chat_context_limit = gr.Number()
            def on_change_chat_context_limit(chat_context_limit):
                config['chat_context_limit'] = int(chat_context_limit)
            chat_context_limit.change(on_change_chat_context_limit, chat_context_limit, None)

            auto_compress_context = gr.Checkbox()
            def on_change_auto_compress_context(auto_compress_context):
                config['auto_compress_context'] = auto_compress_context
            auto_compress_context.change(on_change_auto_compress_context, auto_compress_context, None)
    
    def init_tab():
        openai_api_key = gr.Textbox(label='openai api_key', value=openai_config['api_key'], lines=1, placeholder='这里输入openai api key', interactive=True)
        openai_base_url = gr.Textbox(label='openai base_url', value=openai_config['base_url'], lines=1, placeholder='这里输入openai base url', interactive=True)
        chatgpt_base_url = gr.Textbox(label='chatgpt base_url', value=chatgpt_config['base_url'], lines=1, placeholder='这里输入chatgpt base url', interactive=True)
        baidu_access_key = gr.Textbox(label='baidu access_key', value=baidu_config['access_key'], lines=1, placeholder='这里输入baidu access key', interactive=True)
        baidu_secret_key = gr.Textbox(label='baidu secret_key', value=baidu_config['secret_key'], lines=1, placeholder='这里输入baidu secret key', interactive=True)
        chat_context_limit = gr.Number(label='chat_context_limit', info='llm api的最大上下文长度，超过此长度会调用大模型进行压缩', value=config['chat_context_limit'], interactive=True)
        auto_compress_context = gr.Checkbox(label='auto_compress_context', info='是否自动精简上下文中重复的信息', value=True, interactive=True)
        return openai_api_key, openai_base_url, chatgpt_base_url, baidu_access_key, baidu_secret_key, chat_context_limit, auto_compress_context

    tab.select(init_tab, None, [openai_api_key, openai_base_url, chatgpt_base_url, baidu_access_key, baidu_secret_key, chat_context_limit, auto_compress_context])