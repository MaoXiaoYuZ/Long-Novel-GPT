import os
from prompts.chat_utils import chat
from prompts.prompt_utils import load_jinja2_template
from prompts.common_parser import parse_last_code_block as parser


def main(model, suggestion, context, text=None):
    template = load_jinja2_template(os.path.join(os.path.dirname(os.path.join(__file__)), "prompt.jinja2"))

    prompt = template.render(suggestion=suggestion, 
                             context=context,
                             text=text)
    
    response_msgs = yield from chat([], prompt, model, parse_chat=True)

    newtext = parser(response_msgs)

    return {'text': newtext, 'response_msgs':response_msgs}




