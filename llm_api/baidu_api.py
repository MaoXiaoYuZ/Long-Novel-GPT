import qianfan
from .chat_messages import ChatMessages

# https://console.bce.baidu.com/qianfan/ais/console/applicationConsole/application

wenxin_model_config = {
    "ERNIE-Bot":{
        "Pricing": (0.012, 0.012),
        "currency_symbol": '￥',
    },
    "ERNIE-Bot-4":{
        "Pricing": (0.12, 0.12),
        "currency_symbol": '￥',
    },
}


def stream_chat_with_wenxin(messages, model='ERNIE-Bot', response_json=False, ak=None, sk=None):
    if ak is None or sk is None:
        raise Exception('未提供有效的 ak 和 sk！')

    client = qianfan.ChatCompletion(ak=ak, sk=sk)

    messages = ChatMessages(messages, model=model)
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
            raise e
        else:
            report += f"(Success){model}:{messages.response}(Cost:{messages.cost}{messages.currency_symbol})\n"
    return report
    
if __name__ == '__main__':
    print(test_wenxin_api(ak='your_ak_here', sk='your_sk_here'))