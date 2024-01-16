from openai import OpenAI

from llm_api.chat_messages import ChatMessages

openai_config = {
    'api_key': '',
    'base_url': '',
}

gpt_model_config = {
    "gpt-4-1106-preview":{
        "CONTEXT_WINDOW": 128_000,
        "Pricing": (0.01, 0.03),
    },
    "gpt-3.5-turbo-1106":{
        "CONTEXT_WINDOW": 16_385,
        "Pricing": (0.001, 0.002),
    },
}

client = None

def set_gpt_api_config(**kwargs):
    global client
    openai_config.update(kwargs)
    client = OpenAI(**kwargs)

def count_gpt_api_cost(model, context_tokens, completion_tokens):
    cost = gpt_model_config[model]["Pricing"][0] * context_tokens / 1_000 + gpt_model_config[model]["Pricing"][1] * completion_tokens / 1_000
    return cost

def stream_chat_with_gpt(messages, model='gpt-3.5-turbo-1106', max_tokens=4_096, response_json=False, n=1):
    if client is None:
        raise Exception('未配置openai_api！')
    
    messages = ChatMessages(messages, model=model, currency_symbol='$')
    context_tokens = messages.get_estimated_tokens()
    context_cost = count_gpt_api_cost(model, context_tokens, 0)
    messages.cost = context_cost
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
            messages.cost = count_gpt_api_cost(model, context_tokens, messages[-1:].get_estimated_tokens())
            yield messages

def test_gpt_api():
    report = 'User:Say this is a test\n'
    for model in gpt_model_config:
        try:
            stream = stream_chat_with_gpt([{'role': 'user', 'content': "Say this is a test"}, ], model=model)
            response = list(stream)[-1][-1]['content']
        except Exception as e:
            report += f"(ERROR){model}:{e}\n"
        else:
            report += f"(Success){model}:{response}\n"
    return report
    
    
if __name__ == '__main__':
    print(test_gpt_api())