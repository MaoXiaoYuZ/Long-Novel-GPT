import os
from prompts.chat_utils import chat
from prompts.prompt_utils import parse_chunks_by_separators, match_code_block, load_jinja2_template
from promptflow.tracing import trace


@trace
def parser(response_msgs):
    content = response_msgs[-1]['content']

    chunks = parse_chunks_by_separators(content, [r'\S*', ])
    if "意见" in chunks:
        return chunks["意见"]
    else:
        return content


@trace
def main(model, instruction=None, chunks=None, context=None):
    template = load_jinja2_template(os.path.join(os.path.dirname(os.path.join(__file__)), "prompt.jinja2"))

    prompt = template.render(instruction=instruction, 
                             chunks="\n\n".join([f"###{k}\n{v}" for k, v in chunks.items()]) if chunks else None,
                             context=context)
    
    response_msgs = chat([], prompt, model, parse_chat=True)

    suggestion = parser(response_msgs)

    return {'suggestion': suggestion, 'response_msgs':response_msgs}
    


