import qianfan
from .chat_messages import ChatMessages

# ak和sk获取：https://console.bce.baidu.com/qianfan/ais/console/applicationConsole/application

# 价格：https://cloud.baidu.com/doc/WENXINWORKSHOP/s/hlrk4akp7

wenxin_model_config = {
    "ERNIE-3.5-8K":{
        "Pricing": (0.0008, 0.002),
        "currency_symbol": '￥',
    },
    "ERNIE-4.0-8K":{
        "Pricing": (0.03, 0.09),
        "currency_symbol": '￥',
    },
}


def stream_chat_with_wenxin(messages, model='ERNIE-Bot', response_json=False, ak=None, sk=None, max_tokens=4000):
    if ak is None or sk is None:
        raise Exception('未提供有效的 ak 和 sk！')

    client = qianfan.ChatCompletion(ak=ak, sk=sk)

    messages = ChatMessages(messages, model=model)

    if messages.count_message_tokens() > max_tokens:
        raise Exception(f'请求的文本过长，超过最大tokens:{max_tokens}。')
    
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
        yield messages
    
    return messages

def test_wenxin_api(ak, sk):
    report = 'User:回答这是一个测试。\n'
    for model in wenxin_model_config:
        try:
            stream = stream_chat_with_wenxin([{'role': 'user', 'content': "回答这是一个测试。"}],
                                             model=model,
                                             response_json=False,
                                             ak=ak,
                                             sk=sk)
            messages = list(stream)[-1]
        except Exception as e:
            report += f"(ERROR){model}:{e}\n"
        else:
            report += f"(Success){model}:{messages.response}(Cost:{messages.cost}{messages.currency_symbol})\n"
    return report
    
if __name__ == '__main__':
    print(test_wenxin_api(ak='your_ak_here', sk='your_sk_here'))