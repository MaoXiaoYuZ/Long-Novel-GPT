from collections import defaultdict
import json
from openai import OpenAI

from .chat_messages import ChatMessages

openai_config = {
    'api_key': 'none',
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
    client = OpenAI(**openai_config)

def count_gpt_api_cost(model, context_tokens, completion_tokens):
    cost = gpt_model_config[model]["Pricing"][0] * context_tokens / 1_000 + gpt_model_config[model]["Pricing"][1] * completion_tokens / 1_000
    return cost

def stream_function_calling_with_gpt(messages, tools, model='gpt-3.5-turbo-1106', max_tokens=4_096):
    if client is None:
        raise Exception('未配置openai_api！')
    assert model in gpt_model_config, f"model必须是{list(gpt_model_config.keys())}中的一个！"
    messages = ChatMessages(messages, model=model)
    yield messages
    
    response = client.chat.completions.create(
        stream=True,
        model=model,
        messages=messages,
        tools=tools,
        tool_choice="auto",  # auto is default, but we'll be explicit
    )

    messages.append({'role': 'assistant', 'content': ''})
    function_calls = defaultdict(lambda :{"name": "", "arguments": ""})
    content = ""
    for part in response:
        content += part.choices[0].delta.content or ""
        for delta_tool_call in part.choices[0].delta.tool_calls or []:
            func_call = function_calls[delta_tool_call.index]
            func_call["name"] = delta_tool_call.function.name or func_call["name"]
            func_call["arguments"] += delta_tool_call.function.arguments or ""
        messages[-1]['content'] = content + "\n" + json.dumps(list(function_calls.values()), ensure_ascii=False, indent=1)
        yield messages

    return messages, content, list(function_calls.values())        

def stream_chat_with_gpt(messages, model='gpt-3.5-turbo-1106', max_tokens=4_096, response_json=False, n=1):
    if client is None:
        raise Exception('未配置openai_api！')
    assert model in gpt_model_config, f"model必须是{list(gpt_model_config.keys())}中的一个！"
    messages = ChatMessages(messages, model=model, currency_symbol='$')
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
