import re
import qianfan

from llm_api.chat_messages import ChatMessages

baidu_config = {
    'access_key': '',
    'secret_key': ''
}

wenxin_model_config = {
    "ERNIE-Bot":{
        "Pricing": (0.012, 0.012),
    },
    "ERNIE-Bot-4":{
        "Pricing": (0.12, 0.12),
    },
}

client = None

def set_wenxin_api_config(**kwargs):
    global client
    baidu_config.update(kwargs)
    client = qianfan.ChatCompletion(**baidu_config)

def count_wenxin_api_cost(model, context_tokens, completion_tokens):
    cost = wenxin_model_config[model]["Pricing"][0] * context_tokens / 1_000 + wenxin_model_config[model]["Pricing"][1] * completion_tokens / 1_000
    return cost

def stream_chat_with_wenxin(messages, model='ERNIE-Bot', response_json=False):
    if client is None:
        raise Exception('未配置文心一言api！')

    messages = ChatMessages(messages, model=model, currency_symbol='￥')
    context_tokens = messages.get_estimated_tokens()
    context_cost = count_wenxin_api_cost(model, context_tokens, 0)
    messages.cost = context_cost
    yield messages
    
    chatstream = client.do(model=model, 
                           system=messages[0]['content'] if messages[0]['role'] == 'system' else None,
                           messages=messages if messages[0]['role'] != 'system' else messages[1:], 
                           stream=True, 
                           )
    
    messages.append({'role': 'assistant', 'content': ''})
    content = ''
    for part in chatstream:
        content += part['body']['result'] or ''
        messages[-1]['content'] = content
        messages.cost = count_wenxin_api_cost(model, context_tokens, messages[-1:].get_estimated_tokens())
        yield messages
    
    if response_json:
        pattern = r'```json(.*?)```'
        match = re.search(pattern, messages[-1]['content'], re.DOTALL)

        if match:
            messages[-1]['content'] = match.group(1)
            yield messages
        else:
            raise Exception('无法解析文心一言返回结果！')

def test_wenxin_api():
    report = 'User:回答这是一个测试。\n'
    for model in wenxin_model_config:
        try:
            stream = stream_chat_with_wenxin([{'role': 'user', 'content': "回答这是一个测试。"}, ], model=model, response_json=False)
            response = list(stream)[-1][-1]['content']
        except Exception as e:
            report += f"(ERROR){model}:{e}\n"
        else:
            report += f"(Success){model}:{response}\n"
    return report
    
    
if __name__ == '__main__':
    print(test_wenxin_api())