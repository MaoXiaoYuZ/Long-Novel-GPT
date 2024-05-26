import difflib
import json
import yaml
from jinja2 import Environment, FileSystemLoader  

import re
import sys, os
root_path = os.path.abspath(os.path.join(os.path.abspath(__file__), "../.."))
if root_path not in sys.path:
    sys.path.append(root_path)

from llm_api.chat_messages import ChatMessages
from llm_api.chatgpt_api import match_first_json_block

def parse_first_json_block(response_msgs: ChatMessages):
    assert response_msgs[-1]['role'] == 'assistant'
    return json.loads(match_first_json_block(response_msgs[-1]['content']))

def match_code_block(response):
    response = re.sub(r'\r\n', r'\n', response)
    response = re.sub(r'\r', r'\n', response)
    pattern = r"(?<=[\n])```(?:\S*\s)(.*?)```(?=[\n])"
    matches = re.findall(pattern, '\n' + response + '\n```\n', re.DOTALL)
    return matches

def json_dumps(json_object):
    return json.dumps(json_object, ensure_ascii=False, indent=1)

def parse_chunks_by_separators(string, separators):
    separator_pattern = r"^\s*###\s*(" + "|".join(separators) + r")\s*\n"

    chunks = re.split(separator_pattern, string, flags=re.MULTILINE)

    ret = {}

    current_title = None
    
    for i, chunk in enumerate(chunks):
        if i % 2 == 1: 
            current_title = chunk.strip()
            ret[current_title] = ""
        elif current_title:
            ret[current_title] += chunk.strip()

    return ret

def construct_chunks_and_separators(chunk2separator):
    return "\n\n".join([f"### {k}\n{v}" for k, v in chunk2separator.items()])

def match_chunk_span_in_text(chunk, text):
    diff = difflib.Differ().compare(chunk, text)

    chunk_i = 0
    text_i = 0

    for tag in diff:
        if tag.startswith(' '):
            chunk_i += 1
            text_i += 1
        elif tag.startswith('+'):
            text_i += 1
        else:
            chunk_i += 1
        
        if chunk_i == 1:
            l = text_i - 1
        
        if chunk_i == len(chunk):
            r = text_i
            return l, r

def load_yaml(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:  
        return yaml.safe_load(file)  
    
def load_jinja2_template(file_path):
    env = Environment(loader=FileSystemLoader(os.path.dirname(file_path)))
    template = env.get_template(os.path.basename(file_path)) 

    return template 


