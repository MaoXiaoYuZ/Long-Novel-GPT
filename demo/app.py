import json
import os
import time
import gradio as gr
import random
from glob import glob

import sys
sys.path.append(os.path.abspath(os.path.join(__file__, '../..')))

from demo.tab_main_page import tab_main_page
from demo.tab_outline_writer import tab_outline_writer
from demo.tab_chapters_writer import tab_chapters_writer
from demo.tab_novel_writer import tab_novel_writer
from demo.tab_setting import tab_setting

info = \
"""1. GPT-3.5可能不足以生成达到签约或出版水平的小说，请优先选择GPT-4 API。
2. 请在**设置**页面中配置OpenAI API，否则无法使用。
3. 前四个页面的顺序是固定的，必须按照顺序依次生成小说名/大纲/章节/正文，且每一个页面依赖上一个页面的结果。
4. 如果遇到任何无法解决的问题，请尝试刷新页面或重启程序。
"""

with gr.Blocks() as demo:
    gr.Markdown("# Long-Novel-GPT")
    with gr.Accordion("使用指南"):
        gr.Markdown(info)
    config = {'lngpt': None, 'chat_context_limit': 2000}
    tab_main_page(config)
    tab_outline_writer(config)
    tab_chapters_writer(config)
    tab_novel_writer(config)
    tab_setting(config)

if __name__ == "__main__":
    demo.queue()
    demo.launch(share=False)
