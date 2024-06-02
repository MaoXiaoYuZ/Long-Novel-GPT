import os
from prompts.chat_utils import chat
from prompts.prompt_utils import load_jinja2_template
from prompts.common_parser import parse_named_chunk


def parser(response_msgs):
    return parse_named_chunk(response_msgs, '意见')


def main(model, instruction, text, context):
    template = load_jinja2_template(os.path.join(os.path.dirname(os.path.join(__file__)), "prompt.jinja2"))

    prompt = template.render(instruction=instruction, 
                             text=text,
                             context=context)
    
    response_msgs = yield from chat([], prompt, model, parse_chat=True)

    suggestion = parser(response_msgs)

    return {'suggestion': suggestion, 'response_msgs':response_msgs}
    


