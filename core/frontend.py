import gradio as gr
import yaml

import time
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.backend import call_write_all, call_rewrite_suggestion, call_rewrite_text, call_accept
from llm_api.baidu_api import test_wenxin_api
from llm_api import ModelConfig, wenxin_model_config


# 前端实现
def new_pair(a, b):
    return dict(
        a=a, b=b,
        a_source_index=None,
        sub_win_open=False,
        prompt_win = dict(
            open=True,
            prompts=['默认Prompt'],
            selected_prompt=None,
            default_prompt='默认Prompt',
        ),
        suggestion_win = dict(
            open=False,
            output_suggestion='',
        ),
        text_win = dict(
            open=False,
            output_text='',
        ),
        render_count=0
    )

def new_writer(texta, textb):
    return dict(
        texta=texta, textb=textb,
        current_cost=0,
        total_cost=0,
        current_operation=None,
        currency_symbol='￥',
        render_count=0,
        stop=False
    )

ak, sk = '', ''

def new_setting():
    return dict(
        model=ModelConfig(
            model='ERNIE-4.0-8K',
            ak=ak,
            sk=sk,
            max_tokens=4000
        ),
        sub_model=ModelConfig(
            model='ERNIE-3.5-8K',
            ak=ak,
            sk=sk,
            max_tokens=4000
        ),
        render_count=0
    )


# 读取YAML文件
with open('tests/examples/text-plot-examples.yaml', 'r', encoding='utf-8') as file:
    examples_data = yaml.safe_load(file)

# 准备示例列表
examples = [[example['plot']] for example in examples_data['examples']]

title = """
<div style="text-align: center; padding: 10px 20px;">
    <h1 style="margin: 0 0 5px 0;">🖋️ Long-Novel-GPT 1.6</h1>
    <p style="margin: 0;"><em>让每个人都能轻松创作自己心目中的小说</em></p>
</div>
"""

info = \
"""1. 当前Demo已经配置了API-Key，可以直接使用。
2. 当前Demo仅展示了 提纲->正文 的部分，后续版本会陆续支持大纲和章节的生成，最终将实现完整的长文本小说生成。
3. 可以选中**示例**中的任意一个提纲，然后点击**创作全部正文**来生成正文。也可自行输入提纲。
4. 通过**重写**功能可以对正文中任意选中段落进行修改。在**重写**时可以多次生成建议或文本，也可手动对生成的建议或文本进行修改。
5. 如果遇到任何无法解决的问题，请在**手动备份重要文本**后尝试**刷新**页面。
"""

with gr.Blocks() as demo:
    gr.HTML(title)
    with gr.Accordion("使用指南"):
        gr.Markdown(info)

    writer_state = gr.State(new_writer('', ''))
    pair_state = gr.State(new_pair('', ''))
    setting_state = gr.State(new_setting())

    with gr.Row():
        textbox_a = gr.Textbox(placeholder="可以从底部示例中选择提纲或自行输入。", label="提纲", lines=10, interactive=True, show_copy_button=True)
        textbox_b = gr.Textbox(placeholder="点击创作全部正文来生成，点击重写来对选中段落进行修改...",
                                label="正文", lines=10, interactive=True, show_copy_button=True)

        def on_select_inputs(evt: gr.SelectData, pair): 
            if pair['a_source_index'] is not None and tuple(pair['a_source_index']) == tuple(evt.index):
                raise Exception('重复选择相同的文本段')  # bug:在选中后点击重写按钮会重新触发select事件，故这里进行判定
            else:
                # gr.Info(f"You selected {evt.value} at {evt.index} from {evt.target}")
                print(tuple(evt.index))
                pair = new_pair(evt.value, '')
                pair['a_source_index'] = tuple(evt.index)
            return pair
        

        textbox_b.select(on_select_inputs, pair_state, pair_state)
    
    
    with gr.Row():
        write_all_button = gr.Button("创作全部正文", scale=3, min_width=1, variant='primary')

        stop_button = gr.Button("中止", scale=1, min_width=1, variant='secondary')  # 新按钮

    def on_write_all(textbox_a, textbox_b, writer, setting):
        writer['texta'] = textbox_a
        writer['textb'] = textbox_b

        if not setting['model']['ak'] or not setting['model']['sk']:
            gr.Info('请先在API设置中配置api-key！')
            yield writer['textb'], writer
            return
        
        if not textbox_a:
            gr.Info('请先输入提纲！')
            yield writer['textb'], writer
            return
        
        try:
            for chunk in call_write_all(writer, setting):
                yield chunk, gr.update()
        except Exception as e:
            gr.Info(str(e))

        yield writer['textb'], writer
    
    click_handle = write_all_button.click(
            on_write_all,
            queue=True,
            inputs=[textbox_a, textbox_b, writer_state, setting_state],
            outputs=[textbox_b, writer_state],
            concurrency_limit=10
        )

    stop_button.click(fn=None, inputs=None, outputs=None, cancels=[click_handle, ])
    

    @gr.render(inputs=pair_state)
    def render_pair(pair):
        # 似乎on_render中pair发生改变，render才会正常工作
        def on_render():
            pair['render_count'] += 1
            return pair

        with gr.Row():
            #paira = gr.Textbox(pair['a'], key=f"paira-{pairi}", label=None, show_label=False, container=False, interactive=True, lines=2)
            paira = gr.Textbox(pair['a'], label=None, show_label=False, container=False, interactive=False, lines=2, scale=10,
                               placeholder="从上方文本框中选择需要创作的文本..."
                               )
            rewrite_button = gr.Button("重写", scale=1, min_width=1, variant='primary' if pair['a'] and not pair['b'] else 'secondary')
            #pairb = gr.Textbox(pair['b'], key=f"pairb-{pairi}", label=None, show_label=False, container=False, interactive=True, lines=2)
            pairb = gr.Textbox(pair['b'], label=None, show_label=False, container=False, interactive=True, lines=2, scale=10)
            accept_button = gr.Button("接受", scale=1, min_width=1, variant= 'primary' if pair['a'] and pair['b'] else 'secondary')

            def on_config(textbox_a, textbox_b, paira, pairb, writer, setting):
                print('on_config start', pair['sub_win_open'], 'render_count', pair['render_count'])
                if not paira:
                    raise gr.Error('先从正文中选择需要重写的段落！')
                
                writer['texta'] = textbox_a
                writer['textb'] = textbox_b

                pair['b'] = ''
                pair.update({k: v for k, v in new_pair(paira, pairb).items() if k in ['prompt_win', 'suggestion_win', 'text_win']})
                pair['render_count'] += 1
                pair['sub_win_open'] = not pair['sub_win_open']
                print('on_config return', pair['sub_win_open'], 'render_count', pair['render_count'])
                return pair
            
            rewrite_button.click(fn=on_config, inputs=[textbox_a, textbox_b, paira, pairb, writer_state, setting_state], outputs=[pair_state])

            def on_accept(textbox_a, textbox_b, pairb, writer, setting):
                if pair['a_source_index'] is None:
                    raise gr.Error('未选择需要重写的文本段')
                if pairb == '':
                    raise gr.Error('未生成文本')
                
                if textbox_b[pair['a_source_index'][0]:pair['a_source_index'][1]] != pair['a']:
                    raise gr.Error('需要重写的正文被中途修改，请手动修改。')
                
                writer['textb'] = textbox_b
                writer['texta'] = textbox_a

                pair['b'] = pairb
                call_accept(writer, pair, setting)
                return writer

            accept_button.click(fn=on_accept, inputs=[textbox_a, textbox_b, pairb, writer_state, setting_state], outputs=[writer_state]).success(
                lambda writer: (writer['textb'], new_pair('', '')), writer_state, [textbox_b, pair_state])

        if pair['sub_win_open']:
            with gr.Accordion():
                with gr.Column():
                    prompt_win = pair['prompt_win']
                    if prompt_win['open']:
                        with gr.Row():
                            prompts_button = gr.Button("选择Prompt", scale=1, interactive=True)
                            prompts_gradio = gr.Radio(choices=prompt_win['prompts'], value=prompt_win['selected_prompt'], label=None, show_label=False, scale=4)

                            def on_select_prompt(selected_prompt):
                                pair['prompt_win']['selected_prompt'] = selected_prompt
                                pair['suggestion_win']['open'] = True
                                return pair

                            prompts_gradio.select(fn=on_select_prompt, inputs=prompts_gradio, outputs=[pair_state])
                            prompts_button.click(fn=lambda: on_select_prompt(pair['prompt_win']['default_prompt']), inputs=None, outputs=[pair_state])
                    else:
                        pair['suggestion_win']['open'] = False
                    
                    suggestion_win = pair['suggestion_win']
                    if suggestion_win['open']:
                        with gr.Row():
                            suggestion_button = gr.Button("生成建议", scale=1)
                            output_suggestion = gr.Textbox(pair['suggestion_win']['output_suggestion'], label=None, show_label=False, container=False, interactive=True, lines=1, scale=4)

                            def on_gen_suggestion(writer, setting):
                                import time
                                
                                try:
                                    suggestion = yield from call_rewrite_suggestion(writer, pair, setting)
                                except Exception as e:
                                    raise gr.Error(str(e))

                                pair['text_win']['open'] = True
                                yield suggestion
                            
                            suggestion_button.click(fn=on_gen_suggestion, inputs=[writer_state, setting_state], outputs=[output_suggestion]).success(
                                fn=on_render, inputs=None, outputs=[pair_state]
                            )
                    
                    text_win = pair['text_win']
                    if text_win['open']:
                        with gr.Row():
                            text_button = gr.Button("生成文本", scale=1)
                            output_text = gr.Textbox(pair['text_win']['output_text'], label=None, show_label=False, container=False, interactive=True, lines=1, scale=4)

                            def on_gen_text(output_suggestion, writer, setting):
                                pair['suggestion_win']['output_suggestion'] = output_suggestion
                                try:    
                                    text = yield from call_rewrite_text(writer, pair, setting)
                                except Exception as e:
                                    raise gr.Error(str(e))

                                yield text
                            
                            text_button.click(fn=on_gen_text, inputs=[output_suggestion, writer_state, setting_state], outputs=[output_text]).success(
                                fn=on_render, inputs=None, outputs=[pair_state]
                            )

    @gr.render(inputs=setting_state)
    def render_setting(setting):
        def on_render():
            setting['render_count'] += 1
            return setting

        with gr.Accordion("API 设置"):
            with gr.Row():
                baidu_access_key = gr.Textbox(
                    value=setting['model']['ak'],
                    label='Baidu Access Key',
                    lines=1,
                    placeholder='Enter your Baidu access key here',
                    interactive=True,
                    scale=10,
                    type='password'
                )
                baidu_secret_key = gr.Textbox(
                    value=setting['model']['sk'],
                    label='Baidu Secret Key',
                    lines=1,
                    placeholder='Enter your Baidu secret key here',
                    interactive=True,
                    scale=10,
                    type='password'
                )

                test_baidu_button = gr.Button('测试', scale=1)
            
            baidu_report = gr.Textbox(key='baidu_report', label='测试结果', value='', interactive=False)
            
            def on_test_baidu_api(access_key, secret_key):
                for modelconfig in [setting['model'], setting['sub_model']]:
                    modelconfig['ak'] = access_key
                    modelconfig['sk'] = secret_key
                    
                setting['model'] = ModelConfig(**setting['model'])
                setting['sub_model'] = ModelConfig(**setting['sub_model'])
                result = test_wenxin_api(setting['model']['ak'], setting['model']['sk'])
                return result, setting
            
            test_baidu_button.click(
                on_test_baidu_api,
                inputs=[baidu_access_key, baidu_secret_key],
                outputs=[baidu_report, setting_state]
            ).then(on_render, None, setting_state)

    gr.Examples(
        label='示例',
        examples=examples,
        inputs=[textbox_a],
    )

demo.queue()
demo.launch(server_name="0.0.0.0", server_port=7860)
#demo.launch()
