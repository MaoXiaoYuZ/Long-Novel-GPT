from zhipuai import ZhipuAI
from .chat_messages import ChatMessages

# Pricing
# https://open.bigmodel.cn/pricing
# GLM-4-Plus 0.05￥/1000 tokens, GLM-4-Air 0.001￥/1000 tokens, GLM-4-FlashX 0.0001￥/1000 tokens, , GLM-4-Flash 0￥/1000 tokens

# Models
# https://bigmodel.cn/dev/howuse/model
# glm-4-plus、glm-4-air、 glm-4-flashx 、 glm-4-flash



zhipuai_model_config = {
    "glm-4-plus": {
        "Pricing": (0.05, 0.05),
        "currency_symbol": '￥',
    },
    "glm-4-air": {
        "Pricing": (0.001, 0.001),
        "currency_symbol": '￥',
    },
    "glm-4-flashx": {
        "Pricing": (0.0001, 0.0001),
        "currency_symbol": '￥',
    },
    "glm-4-flash": {
        "Pricing": (0, 0),
        "currency_symbol": '￥',
    },
}

def stream_chat_with_zhipuai(messages, model='glm-4-flash', response_json=False, api_key=None, max_tokens=4_096):
    if api_key is None:
        raise Exception('未提供有效的 api_key！')
    
    client = ZhipuAI(api_key=api_key)

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        max_tokens=max_tokens
    )
    
    messages.append({'role': 'assistant', 'content': ''})
    for chunk in response:
        messages[-1]['content'] += chunk.choices[0].delta.content or ''
        yield messages
    
    return messages

if __name__ == '__main__':
    pass