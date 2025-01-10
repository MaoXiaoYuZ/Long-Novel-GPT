import os
import re
from prompts.chat_utils import chat, log
from prompts.baseprompt import parse_prompt, load_prompt
from prompts.common_parser import parse_last_code_block as parser


def main(model, user_prompt, **kwargs):
    assert 'y' in kwargs, 'y must in kwargs'

    dirname = os.path.dirname(__file__)

    messages = parse_prompt(load_prompt(dirname, user_prompt), **kwargs)
     
    for response_msgs in chat(messages, None, model, parse_chat=False):
        text = parser(response_msgs)
        ret = {'text': text, 'response_msgs': response_msgs, 'text_key': 'x_chunk'}
        yield ret

    return ret



