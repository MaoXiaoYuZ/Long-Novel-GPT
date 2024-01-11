from openai import OpenAI

def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0613"):
    """Returns the number of tokens used by a list of messages."""
    """粗略估计"""
    num_tokens = 0
    for message in messages:
        num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
        for key, value in message.items():
            num_tokens += len(value)
            if key == "name":  # if there's a name, the role is omitted
                num_tokens += -1  # role is always required and always 1 token
    num_tokens += 2  # every reply is primed with <im_start>assistant
    return num_tokens

openai_config = {
    'api_key': '',
    'base_url': '',
}

client = None

def set_gpt_api_config(**kwargs):
    global client
    openai_config.update(kwargs)
    client = OpenAI(**kwargs)

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

def count_gpt_api_cost(model, context_tokens, completion_tokens):
    if isinstance(context_tokens, list|tuple):
        context_tokens = num_tokens_from_messages(context_tokens, model)
    cost = gpt_model_config[model]["Pricing"][0] * context_tokens / 1_000 + gpt_model_config[model]["Pricing"][1] * completion_tokens / 1_000
    return cost

def stream_chat_with_gpt(messages, model='gpt-3.5-turbo-1106', max_tokens=4_096, response_format=None, n=1):
    if client is None:
        raise Exception('未配置openai_api！')
    chatstream = client.chat.completions.create(
                stream=True,
                model=model, 
                messages=messages, 
                max_tokens=max_tokens,
                response_format=response_format,
                n=n
                )
    content = ['' for _ in range(n)]
    for part in chatstream:
        for choice in part.choices:
            content[choice.index] += choice.delta.content or ''
            yield content if n > 1 else content[0]

def test_gpt_api():
    report = 'User:Say this is a test\n'
    for model in gpt_model_config:
        try:
            stream = stream_chat_with_gpt([{'role': 'user', 'content': "Say this is a test"}, ], model=model)
            response = list(stream)[-1]
        except Exception as e:
            report += f"(ERROR){model}:{e}\n"
        else:
            report += f"(Success){model}:{response}\n"
    return report
    
    
if __name__ == '__main__':
    print(test_gpt_api())