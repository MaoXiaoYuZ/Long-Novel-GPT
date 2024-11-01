from openai import OpenAI
from .chat_messages import ChatMessages

# Pricing reference: https://openai.com/api/pricing/
gpt_model_config = {
    "gpt-4o": {
        "Pricing": (2.50/1000, 10.00/1000),
        "currency_symbol": '$',
    },
    "gpt-4o-mini": {
        "Pricing": (0.15/1000, 0.60/1000),
        "currency_symbol": '$',
    },
    "o1-preview": {
        "Pricing": (15/1000, 60/1000),
        "currency_symbol": '$',
    },
    "o1-mini": {
        "Pricing": (3/1000, 12/1000),
        "currency_symbol": '$',
    },
}


def stream_chat_with_gpt(messages, model='gpt-3.5-turbo-1106', response_json=False, api_key=None, base_url=None, max_tokens=4_096, n=1):
    if api_key is None:
        raise Exception('未提供有效的 api_key！')
    
    client = OpenAI(api_key=api_key, base_url=base_url)

    if model in ['o1-preview', ] and messages[0]['role'] == 'system':
        messages[0:1] = [{'role': 'user', 'content': messages[0]['content']}, {'role': 'assistant', 'content': ''}]
    
    messages = ChatMessages(messages, model=model)
    
    if messages.count_message_tokens() > max_tokens:
        raise Exception(f'请求的文本过长，超过最大tokens:{max_tokens}。')
    
    yield messages
    
    chatstream = client.chat.completions.create(
        stream=True,
        model=model, 
        messages=messages, 
        max_tokens=max_tokens,
        response_format={ "type": "json_object" } if response_json else None,
        n=n
    )
    
    messages.append({'role': 'assistant', 'content': ''})
    content = ['' for _ in range(n)]
    for part in chatstream:
        for choice in part.choices:
            content[choice.index] += choice.delta.content or ''
            messages[-1]['content'] = content if n > 1 else content[0]
            yield messages
    
    return messages

    
if __name__ == '__main__':
    pass
