import os
from prompts.chat_utils import chat
from prompts.prompt_utils import load_jinja2_template
from prompts.common_parser import parse_last_code_block as parser


# 生成重写正文的意见
def main(model, chapter, text, selected_text):
    template = load_jinja2_template(os.path.join(os.path.dirname(os.path.join(__file__)), "prompt.jinja2"))

    prompt = template.render(chapter=chapter, 
                             text=text,
                             selected_text=selected_text)
    
    for response_msgs in chat([], prompt, model, parse_chat=True):
        suggestion = parser(response_msgs)
        ret = {'suggestion': suggestion, 'response_msgs':response_msgs}
        yield ret
    
    return ret



