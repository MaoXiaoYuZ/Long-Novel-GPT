from promptflow.core import tool
from promptflow.tools.common import parse_chat as pf_parse_chat

import sys, os
root_path = os.path.abspath(os.path.join(os.path.abspath(__file__), "../.."))
if root_path not in sys.path:
    sys.path.append(root_path)

try:
    import demo.config
except Exception:
    pass

from llm_api.chat_messages import ChatMessages
from llm_api.openai_api import stream_chat_with_gpt
from llm_api.chatgpt_api import stream_chat_with_chatgpt
from llm_api.baidu_api import stream_chat_with_wenxin
from demo.main_chat_messages import update_main_chat_messages

def _chat(messages, model, max_tokens=4000, response_json=False, n=1):
    if 'chatgpt' in model:
        ret = yield from stream_chat_with_chatgpt(messages, model=model, max_tokens=max_tokens, response_json=response_json, n=n)
    elif 'gpt' in model:
        ret = yield from stream_chat_with_gpt(messages, model=model, max_tokens=max_tokens, response_json=response_json, n=n)
    elif 'ERNIE' in model:
        ret = yield from stream_chat_with_wenxin(messages, model=model, response_json=response_json)
    else:
        raise NotImplementedError(f"未知的model:{model}！")
    return ret

@tool
def chat(messages, prompt, model, max_tokens=4000, response_json=False, echo=True, parse_chat=False):
    if prompt:
        if parse_chat:
            messages = pf_parse_chat(prompt)
        else:
            messages = messages + [{'role': 'user', 'content': prompt}]

    gen = _chat(messages, model, max_tokens=max_tokens, response_json=response_json, n=1)
    try:
        while True:
            msgs = next(gen)
            if echo:
                update_main_chat_messages(msgs)
    except StopIteration as e:
        return e.value