import gradio as gr

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
        currency_symbol='￥',
        render_count=0,
        stop=False  # 初始化中止标志
    )

def new_setting():
    return dict(
        model=ModelConfig(
            model='ERNIE-Bot-4',
            ak='wHd0XkepKsUepy3pPQZbx292',
            sk='p6q43UH5R8M5DyrGoUK7nyWZy4GjOdfp'
        ),
        sub_model=ModelConfig(
            model='ERNIE-Bot',
            ak='wHd0XkepKsUepy3pPQZbx292',
            sk='p6q43UH5R8M5DyrGoUK7nyWZy4GjOdfp'
        ),
        render_count=0
    )

test_plot = """
班会开始了。黄洁问第一题：“歌剧《茶花女》的作者是谁？”

舒轼站起来回答：“法国作家，小仲马。”

王天心里觉得简单，希望第一个组答错。未来人老王说答错了。王天习惯了老王的存在，觉得他不该犯错。

黄洁宣布：“错误！”

全场惊讶，尤其是王天。黄洁解释，是问歌剧《茶花女》，而不是小说，让舒轼准备表演节目。第一组没人再答。

黄洁问其他组有人知道答案吗？

老王说：“意大利歌剧作家，威尔第。” 王天立刻回答。

黄洁确认正确，第二组加一分并在黑板上记录。王天得意，杨羊夸他，他勉强装作平静。

老王懒洋洋地说王天笑得难看，但王天没反驳。舒轼朗诵结束，第二组开始答题。
"""

with gr.Blocks() as demo:
    gr.Markdown("# Long-Novel-GPT 1.5")

    writer_state = gr.State(new_writer('afjwoejfoiwejfoawjei\nlefzc.mb.zxmv.zxmv.' * 4, ''))
    pair_state = gr.State(new_pair('', ''))
    setting_state = gr.State(new_setting())

    @gr.render(inputs=writer_state)
    def render_writer(writer):
        def on_render():
            writer['render_count'] += 1
            return writer

        with gr.Row():
            textbox_a = gr.Textbox(value=writer['texta'], label="提纲", lines=10, interactive=True, show_copy_button=True)
            textbox_b = gr.Textbox(value=writer['textb'], label="正文", lines=10, interactive=True, show_copy_button=True)

            def on_select_inputs(evt: gr.SelectData, pair): 
                if pair['a_source_index'] is not None and tuple(pair['a_source_index']) == tuple(evt.index):
                    raise Exception('重复选择相同的文本段')  # bug:在选中后点击重写按钮会重新触发select事件，故这里进行判定
                else:
                    gr.Info(f"You selected {evt.value} at {evt.index} from {evt.target}")
                    print(tuple(evt.index))
                    pair = new_pair(evt.value, '')
                    pair['a_source_index'] = tuple(evt.index)
                return pair
            
            def on_focus_inputs(): 
                #gr.Info("You focus!")
                pass

            def on_blur_inputs(): 
                # gr.Info("You blur!")
                pass

            textbox_b.select(on_select_inputs, pair_state, pair_state)
            # textbox_b.blur(on_blur_inputs)
            # textbox_b.focus(on_focus_inputs, None, None)
        
        gr.Markdown(f"当前操作花费：{writer['current_cost']:.4f}{writer['currency_symbol']}")

        with gr.Row():
            write_all_button = gr.Button("创作全部正文", scale=3, min_width=1, variant='primary' if not writer['textb'] else 'secondary')

            stop_button = gr.Button("中止", scale=1, min_width=1, variant='secondary')  # 新按钮

        def on_write_all(textbox_a, setting):
            writer['texta'] = textbox_a
            writer['stop'] = False  # 重置中止标志

            for chunk in call_write_all(writer, setting):
                yield chunk
                if writer.get('stop'):
                    break  # 检测到中止信号，终止生成
        
        write_all_button.click(lambda: new_pair('', ''), None, [pair_state]).then(
                on_write_all,
                inputs=[textbox_a, setting_state],
                outputs=[textbox_b]
            ).success(
                on_render, None, [writer_state]
            )

        # “中止”按钮的处理函数
        def on_stop():
            writer['stop'] = True
            return writer

        stop_button.click(on_stop)
    

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

            def on_config(paira, pairb):
                print('on_config start', pair['sub_win_open'], 'render_count', pair['render_count'])
                if not paira:
                    raise gr.Error('先从正文中选择需要重写的段落！')
                
                pair['b'] = ''
                pair.update({k: v for k, v in new_pair(paira, pairb).items() if k in ['prompt_win', 'suggestion_win', 'text_win']})
                pair['render_count'] += 1
                pair['sub_win_open'] = not pair['sub_win_open']
                print('on_config return', pair['sub_win_open'], 'render_count', pair['render_count'])
                return pair
            
            rewrite_button.click(fn=on_config, inputs=[paira, pairb], outputs=[pair_state])

            def on_accept(writer, pairb, setting):
                if pair['a_source_index'] is None:
                    raise gr.Error('未选择需要重写的文本段')
                if pairb == '':
                    raise gr.Error('未生成文本')
                
                if writer['textb'][pair['a_source_index'][0]:pair['a_source_index'][1]] != pair['a']:
                    raise gr.Error('需要重写的正文被中途修改，请手动修改。')
                    
                pair['b'] = pairb
                call_accept(writer, pair, setting)
                return writer

            accept_button.click(fn=on_accept, inputs=[writer_state, pairb, setting_state], outputs=[writer_state]).success(
                lambda: new_pair('', ''), None, pair_state
            )

        print('on_render', pair['sub_win_open'], 'render_count', pair['render_count'])
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
                                
                                suggestion = yield from call_rewrite_suggestion(writer, pair, setting)

                                pair['text_win']['open'] = True
                                return suggestion
                            
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

                                text = yield from call_rewrite_text(writer, pair, setting)

                                return text
                            
                            text_button.click(fn=on_gen_text, inputs=[output_suggestion, writer_state, setting_state], outputs=[output_text]).success(
                                fn=on_render, inputs=None, outputs=[pair_state]
                            )
    

    example_textbox = gr.Textbox(visible=False)

    def on_example(x):
        writer = new_writer(x, '')
        return writer

    example_textbox.change(on_example, inputs=[example_textbox], outputs=[writer_state])

    gr.Examples(
        examples=[['test1',], ['test3',], [test_plot, ]],
        inputs=[example_textbox],
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
                    scale=10
                )
                baidu_secret_key = gr.Textbox(
                    value=setting['model']['sk'],
                    label='Baidu Secret Key',
                    lines=1,
                    placeholder='Enter your Baidu secret key here',
                    interactive=True,
                    scale=10
                )

                test_baidu_button = gr.Button('测试', scale=1)
            
            baidu_report = gr.Textbox(key='baidu_report', label='测试结果', value='', interactive=False)
            
            def on_test_baidu_api(access_key, secret_key):
                model_name = 'ERNIE-Bot-4'  
                sub_model_name = 'ERNIE-Bot'
                setting['model'] = ModelConfig(model=model_name, ak=access_key, sk=secret_key)
                setting['sub_model'] = ModelConfig(model=sub_model_name, ak=access_key, sk=secret_key)
                result = test_wenxin_api(setting['model']['ak'], setting['model']['sk'])
                return result, setting
            
            test_baidu_button.click(
                on_test_baidu_api,
                inputs=[baidu_access_key, baidu_secret_key],
                outputs=[baidu_report, setting_state]
            ).then(on_render, None, setting_state)

demo.queue()
demo.launch(server_name="0.0.0.0", server_port=7860)
#demo.launch()
