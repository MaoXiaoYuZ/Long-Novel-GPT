import gradio as gr
from enum import Enum, auto

from llm_api import ModelConfig, wenxin_model_config, doubao_model_config, gpt_model_config, zhipuai_model_config, test_stream_chat
from config import API_SETTINGS, RENDER_SETTING_API_TEST_BTN, ENABLE_SETTING_SELECT_SUB_MODEL


class Provider:
    GPT = "GPT(OpenAI)"
    WENXIN = "文心(百度)"
    DOUBAO = "豆包(字节跳动)"
    ZHIPUAI = "GLM(智谱)"
    OTHERS = '其他'

def deep_update(d, u):
    """Recursively update dictionary d with values from dictionary u"""
    for k, v in u.items():
        if isinstance(v, dict) and k in d and isinstance(d[k], dict):
            deep_update(d[k], v)
        else:
            d[k] = v

def new_setting():
    model_config = API_SETTINGS.pop('model')
    sub_model_config = API_SETTINGS.pop('sub_model')

    new_setting = dict(
        model=ModelConfig(**model_config),
        sub_model=ModelConfig(**sub_model_config),
        render_count=0,
        provider_name=Provider.GPT,
        wenxin={
            'ak': '',
            'sk': '',
            'default_model': 'ERNIE-Novel-8K',
            'default_sub_model': 'ERNIE-3.5-8K',
            'available_models': list(wenxin_model_config.keys())
        },
        doubao={
            'api_key': '',
            'main_endpoint_id': '',
            'sub_endpoint_id': '',
            'default_model': 'doubao-pro-32k',
            'default_sub_model': 'doubao-lite-32k',
            'available_models': list(doubao_model_config.keys())
        },
        gpt={
            'api_key': '',
            'base_url': '',
            'proxies': '',
            'default_model': 'gpt-4o',
            'default_sub_model': 'gpt-4o-mini',
            'available_models': list(gpt_model_config.keys())
        },
        zhipuai={
            'api_key': '',
            'default_model': 'glm-4-plus',
            'default_sub_model': 'glm-4-flashx',
            'available_models': list(zhipuai_model_config.keys())
        },
        others={
            'api_key': '',
            'base_url': '',
            'default_model': '',
            'default_sub_model': '',
            'available_models': []
        }
    )

    deep_update(new_setting, API_SETTINGS)

    return new_setting

# @gr.render(inputs=setting_state)
def render_setting(setting, setting_state):
    with gr.Accordion("API 设置"):
        with gr.Row():
            provider_name = gr.Dropdown(
                choices=[Provider.GPT, Provider.WENXIN, Provider.DOUBAO, Provider.ZHIPUAI, Provider.OTHERS],
                value=setting['provider_name'],
                label="模型提供商",
                scale=1
            )

            def on_select_provider(provider_name):
                setting['provider_name'] = provider_name
                return setting
            
            provider_name.select(fn=on_select_provider, inputs=provider_name, outputs=[setting_state])

            match setting['provider_name']:
                case Provider.WENXIN:
                    provider_config = setting['wenxin']
                case Provider.DOUBAO:
                    provider_config = setting['doubao']
                case Provider.GPT:
                    provider_config = setting['gpt']
                case Provider.ZHIPUAI:
                    provider_config = setting['zhipuai']
                case Provider.OTHERS:
                    provider_config = setting['others']

            main_model = gr.Dropdown(
                choices=provider_config['available_models'],
                value=provider_config['default_model'],
                label="主模型",
                scale=1,
                allow_custom_value=setting['provider_name'] == Provider.OTHERS
            )

            sub_model = gr.Dropdown(
                choices=provider_config['available_models'],
                value=provider_config['default_sub_model'],
                label="辅助模型",
                scale=1,
                allow_custom_value=setting['provider_name'] == Provider.OTHERS,
                interactive=ENABLE_SETTING_SELECT_SUB_MODEL
            )

        with gr.Row():
            if setting['provider_name'] == Provider.WENXIN:
                baidu_access_key = gr.Textbox(
                    value=provider_config['ak'],
                    label='Baidu Access Key',
                    lines=1,
                    placeholder='Enter your Baidu access key here',
                    interactive=True,
                    scale=10,
                    type='password'
                )
                baidu_secret_key = gr.Textbox(
                    value=provider_config['sk'],
                    label='Baidu Secret Key',
                    lines=1,
                    placeholder='Enter your Baidu secret key here',
                    interactive=True,
                    scale=10,
                    type='password'
                )

            elif setting['provider_name'] == Provider.DOUBAO:
                doubao_api_key = gr.Textbox(
                    value=provider_config['api_key'],
                    label='Doubao API Key',
                    lines=1,
                    placeholder='Enter your Doubao API key here',
                    interactive=True,
                    scale=10,
                    type='password'
                )
                main_endpoint_id = gr.Textbox(
                    value=provider_config['main_endpoint_id'],
                    label='Main Endpoint ID',
                    lines=1,
                    placeholder='Enter your main endpoint ID here',
                    interactive=True,
                    scale=10,
                    type='password'
                )
                sub_endpoint_id = gr.Textbox(
                    value=provider_config['sub_endpoint_id'],
                    label='Sub Endpoint ID',
                    lines=1,
                    placeholder='Enter your sub endpoint ID here',
                    interactive=True,
                    scale=10,
                    type='password'
                )

            elif setting['provider_name'] in [Provider.GPT, Provider.OTHERS]:
                gpt_api_key = gr.Textbox(
                    value=provider_config['api_key'],
                    label='OpenAI API Key',
                    lines=1,
                    placeholder='Enter your OpenAI API key here',
                    interactive=True,
                    scale=10,
                    type='password'
                )
                base_url = gr.Textbox(
                    value=provider_config['base_url'],
                    label='API Base URL',
                    lines=1,
                    placeholder='Enter API base URL here',
                    interactive=True,
                    scale=10,
                    type='password'
                )

            elif setting['provider_name'] == Provider.ZHIPUAI:
                zhipuai_api_key = gr.Textbox(
                    value=provider_config['api_key'],
                    label='ZhipuAI API Key',
                    lines=1,
                    placeholder='Enter your ZhipuAI API key here',
                    interactive=True,
                    scale=10,
                    type='password'
                )

        with gr.Row():
            if setting['provider_name'] == Provider.WENXIN:
                def on_submit(main_model, sub_model, baidu_access_key, baidu_secret_key):
                    provider_config['ak'] = baidu_access_key
                    provider_config['sk'] = baidu_secret_key

                    setting['model'] = ModelConfig(
                        model=main_model,
                        ak=baidu_access_key,
                        sk=baidu_secret_key,
                        max_tokens=4096
                    ) 
                    setting['sub_model'] = ModelConfig(
                        model=sub_model,
                        ak=baidu_access_key,
                        sk=baidu_secret_key,
                        max_tokens=4096
                    )

                submit_event = dict(
                    fn=on_submit,
                    inputs=[main_model, sub_model, baidu_access_key, baidu_secret_key],
                )

                on_submit(main_model.value, sub_model.value, baidu_access_key.value, baidu_secret_key.value)

                main_model.change(**submit_event)
                sub_model.change(**submit_event)
                baidu_access_key.change(**submit_event)
                baidu_secret_key.change(**submit_event)
            
            elif setting['provider_name'] == Provider.DOUBAO:
                def on_submit(main_model, sub_model, doubao_api_key, main_endpoint_id, sub_endpoint_id):
                    provider_config['api_key'] = doubao_api_key
                    provider_config['main_endpoint_id'] = main_endpoint_id
                    provider_config['sub_endpoint_id'] = sub_endpoint_id
                            
                    setting['model'] = ModelConfig(
                        model=main_model,
                        api_key=doubao_api_key,
                        endpoint_id=main_endpoint_id,
                        max_tokens=4096
                    )
                    setting['sub_model'] = ModelConfig(
                        model=sub_model,
                        api_key=doubao_api_key,
                        endpoint_id=sub_endpoint_id,
                        max_tokens=4096
                    )
                
                submit_event = dict(    
                    fn=on_submit,
                    inputs=[main_model, sub_model, doubao_api_key, main_endpoint_id, sub_endpoint_id],
                )

                on_submit(main_model.value, sub_model.value, doubao_api_key.value, main_endpoint_id.value, sub_endpoint_id.value)

                main_model.change(**submit_event)
                sub_model.change(**submit_event)
                doubao_api_key.change(**submit_event)
                main_endpoint_id.change(**submit_event)
                sub_endpoint_id.change(**submit_event)

            elif setting['provider_name'] in [Provider.GPT, Provider.OTHERS]:
                def on_submit(main_model, sub_model, gpt_api_key, base_url):
                    provider_config['api_key'] = gpt_api_key
                    provider_config['base_url'] = base_url.strip()
                    
                    setting['model'] = ModelConfig(
                        model=main_model,
                        api_key=provider_config['api_key'],
                        base_url=provider_config['base_url'],
                        max_tokens=4096,
                        proxies=provider_config.get('proxies', None),
                    )
                    setting['sub_model'] = ModelConfig(
                        model=sub_model,
                        api_key=provider_config['api_key'],
                        base_url=provider_config['base_url'],
                        max_tokens=4096,
                        proxies=provider_config.get('proxies', None),
                    )
                
                submit_event = dict(
                    fn=on_submit,
                    inputs=[main_model, sub_model, gpt_api_key, base_url],
                )

                on_submit(main_model.value, sub_model.value, gpt_api_key.value, base_url.value)

                main_model.change(**submit_event)
                sub_model.change(**submit_event)
                gpt_api_key.change(**submit_event)
                base_url.change(**submit_event)

            elif setting['provider_name'] == Provider.ZHIPUAI:
                def on_submit(main_model, sub_model, zhipuai_api_key):
                    provider_config['api_key'] = zhipuai_api_key
                    
                    setting['model'] = ModelConfig(
                        model=main_model,
                        api_key=zhipuai_api_key,
                        max_tokens=4096
                    )
                    setting['sub_model'] = ModelConfig(
                        model=sub_model,
                        api_key=zhipuai_api_key,
                        max_tokens=4096
                    )
                
                submit_event = dict(
                    fn=on_submit,
                    inputs=[main_model, sub_model, zhipuai_api_key],
                )

                on_submit(main_model.value, sub_model.value, zhipuai_api_key.value)

                main_model.change(**submit_event)
                sub_model.change(**submit_event)
                zhipuai_api_key.change(**submit_event)

            if RENDER_SETTING_API_TEST_BTN:
                test_btn = gr.Button("测试")
                test_report = gr.Textbox(show_label=False, container=False, value='', interactive=False, scale=10)
        
            def on_test_llm_api():
                if not setting['model']['model'].strip():
                    return gr.Info('主模型名不能为空')
                
                if not setting['sub_model']['model'].strip():
                    return gr.Info('辅助模型名不能为空')

                try:
                    response1 = yield from test_stream_chat(setting['model'])
                    response2 = yield from test_stream_chat(setting['sub_model'])
                    report_text = f"User:1+1=?\n主模型 ：{response1.response}({response1.cost_info})\n辅助模型：{response2.response}({response2.cost_info})\n测试通过！"
                    yield report_text
                except Exception as e:
                    yield f"测试失败：{str(e)}"
            
            if RENDER_SETTING_API_TEST_BTN:
                test_btn.click(
                    on_test_llm_api,
                    outputs=[test_report]
                )