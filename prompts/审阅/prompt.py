import os
import re
from prompts.chat_utils import chat, log
from prompts.baseprompt import parse_prompt, load_prompt


def main(model, prompt_name, **kwargs):
    assert 'y' in kwargs, 'y must in kwargs'

    dirname = os.path.dirname(__file__)

    messages = parse_prompt(load_prompt(dirname, prompt_name), **kwargs)
     
    for response_msgs in chat(messages, None, model, parse_chat=False):
        text = response_msgs.response
        ret = {'text': text, 'response_msgs': response_msgs}
        yield ret

    return ret



