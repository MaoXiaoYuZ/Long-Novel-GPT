from collections import defaultdict
import json
import re
from openai import OpenAI

from llm_api.chat_messages import ChatMessages

chatgpt_config = {
    'api_key': 'none',
    'base_url': '',
}

chatgpt_model_config = {
    "chatgpt":{
        "CONTEXT_WINDOW": 128_000,
        "Pricing": (0, 0),
    }
}

client = None

def set_chatgpt_api_config(**kwargs):
    global client
    chatgpt_config.update(kwargs)
    client = OpenAI(**chatgpt_config)


def count_chatgpt_api_cost(model, context_tokens, completion_tokens):
    cost = chatgpt_model_config[model]["Pricing"][0] * context_tokens / 1_000 + chatgpt_model_config[model]["Pricing"][1] * completion_tokens / 1_000
    return cost

import requests
import ssl
import certifi

MODEL = "chatgpt"
OPENAI_SECRET_KEY = "none"
# Assuming MODEL and OPENAI_SECRET_KEY are defined earlier in your code.

def post_messages(messages):
    # 在某些情况下，连接本地的OpenAI API可能会失败，所以采用requests连接

    import requests
    import certifi

    payload = {
        'model': MODEL,
        'messages': messages
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_SECRET_KEY}"
    }
    if 'base_url' in chatgpt_config:
        assert chatgpt_config['base_url'].endswith('/v1/'), "base_url必须以'/v1/'结尾！"
    url = chatgpt_config['base_url'] + "chat/completions"

    try:
        response = requests.post(url, headers=headers, json=payload, verify=certifi.where())
        
        # Check if the request was successful
        if response.status_code == 200:
            response_data = response.json()
            if "error" in response_data:
                raise Exception(f"OpenAI request failed with error {response_data['error']}")
            return response_data['choices'][0]['message']['content']
        else:
            raise Exception(f"Request failed with status code {response.status_code}")
    except Exception as e:
        raise Exception(f"Request failed: {e}")
    
def can_parse_json(response):
    try:
        json.loads(response)
        return True
    except:
        return False

def match_first_json_block(response):
    if can_parse_json(response):
        return response
    
    pattern = r"(?<=[\r\n])```json(.*?)```(?=[\r\n])"
    matches = re.findall(pattern, '\n' + response + '\n', re.DOTALL)
    if not matches:
        pattern = r"(?<=[\r\n])```(.*?)```(?=[\r\n])"
        matches = re.findall(pattern, '\n' + response + '\n', re.DOTALL)
        
    if matches:
        json_block = matches[0]
        if can_parse_json(json_block):
            return json_block
        else:
            json_block = json_block.replace('\r\n', '')  # 在continue generate情况下，不同部分之间可能有多出的换行符，导致合起来之后json解析失败
            if can_parse_json(json_block):
                return json_block
            else:
                raise Exception(f"无法解析JSON代码块")
    else:
        raise Exception(f"没有匹配到JSON代码块")

def stream_chat_with_chatgpt(messages, model='chatgpt', max_tokens=4_096, response_json=False, n=1):
    if client is None:
        raise Exception('未配置openai_api！')

    messages = ChatMessages(messages, model=model, currency_symbol='$')
    messages.cost = 0
    yield messages
    
    # chatstream = client.chat.completions.create(
    #             model=model, 
    #             messages=messages, 
    #             max_tokens=max_tokens,
    #             response_format={ "type": "json_object" } if response_json else None,
    #             n=n
    #             )
    
    # messages.append({'role': 'assistant', 'content': ''})
    # content = chatstream.choices[0].message.content
    # messages[-1]['content'] = content
    # messages.cost = 0
    # yield messages

    response = post_messages(messages)
    messages.append({'role': 'assistant', 'content': response})
    
    return messages

def test_chatgpt_api():
    report = 'User:Say this is a test\n'
    for model in chatgpt_model_config:
        try:
            stream = stream_chat_with_chatgpt([{'role': 'user', 'content': "Say this is a test"}, ], model=model)
            response = list(stream)[-1][-1]['content']
        except Exception as e:
            import traceback
            traceback.print_exc()
            report += f"(ERROR){model}:{e}\n"
        else:
            report += f"(Success){model}:{response}\n"
    return report
    
    
if __name__ == '__main__':
    # response = post_messages([
    #         {"role": "user", "content": "hello"}
    #     ])
    # print(response)
    #print(test_chatgpt_api())
    import pyperclip
    print(match_first_json_block(pyperclip.paste()))
