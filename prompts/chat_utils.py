from .pf_parse_chat import parse_chat as pf_parse_chat

from llm_api import ModelConfig, stream_chat


def chat(messages, prompt, model:ModelConfig, parse_chat=False, response_json=True):
    if prompt:
        if parse_chat:
            messages = pf_parse_chat(prompt)
        else:
            messages = messages + [{'role': 'user', 'content': prompt}]

    result = yield from stream_chat(model, messages)

    return result
    