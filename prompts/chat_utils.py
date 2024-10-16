import os
from .pf_parse_chat import parse_chat as pf_parse_chat

from llm_api import ModelConfig, stream_chat
from datetime import datetime  # Update this import
import random


def chat(messages, prompt, model:ModelConfig, parse_chat=False, response_json=False):
    if prompt:
        if parse_chat:
            messages = pf_parse_chat(prompt)
        else:
            messages = messages + [{'role': 'user', 'content': prompt}]

    result = yield from stream_chat(model, messages, response_json=response_json)

    return result
    

def log(prompt_name, prompt, parsed_result):
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    random_suffix = random.randint(1000, 9999)
    filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + f"_{prompt_name}_{random_suffix}.txt"
    filepath = os.path.join(output_dir, filename)

    response_msgs = parsed_result['response_msgs']
    response = response_msgs.response
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("----------prompt--------------\n")
        f.write(prompt + "\n\n")
        f.write("----------response-------------\n")
        f.write(response + "\n\n")
        f.write("-----------parse----------------\n")
        for k, v in parsed_result.items():
            if k != 'response_msgs':
                f.write(f"{k}:\n{v}\n\n")
