from openai import OpenAI
from .chat_messages import ChatMessages

doubao_model_config = {
    "doubao-lite-32k":{
        "Pricing": (0.0003, 0.0006),
        "currency_symbol": '￥',
    },
    "doubao-lite-128k":{
        "Pricing": (0.0008, 0.001),
        "currency_symbol": '￥',
    },
    "doubao-pro-32k":{
        "Pricing": (0.0008, 0.002),
        "currency_symbol": '￥',
    },
    "doubao-pro-128k":{
        "Pricing": (0.005, 0.009),
        "currency_symbol": '￥',
    },
}

def stream_chat_with_doubao(messages, model='doubao-lite-32k', endpoint_id=None, response_json=False, api_key=None, max_tokens=32000):
    if api_key is None:
        raise Exception('未提供有效的 api_key！')
    if endpoint_id is None:
        raise Exception('未提供有效的 endpoint_id！')

    client = OpenAI(
        api_key=api_key,
        base_url="https://ark.cn-beijing.volces.com/api/v3",
    )

    messages = ChatMessages(messages, model=model)

    if messages.count_message_tokens() > max_tokens:
        raise Exception(f'请求的文本过长，超过最大tokens:{max_tokens}。')
    
    yield messages
    
    stream = client.chat.completions.create(
        model=endpoint_id,
        messages=messages,
        stream=True,
        response_format={ "type": "json_object" } if response_json else None
    )

    messages.append({'role': 'assistant', 'content': ''})
    content = ''
    for chunk in stream:
        if chunk.choices:
            delta_content = chunk.choices[0].delta.content or ''
            content += delta_content
            messages[-1]['content'] = content
            yield messages
    
    return messages

if __name__ == '__main__':
    pass
