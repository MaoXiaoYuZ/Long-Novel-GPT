import os
from prompts.chat_utils import chat
from prompts.prompt_utils import parse_chunks_by_separators, match_code_block, load_jinja2_template


def parser(response_msgs, chunks):
    content = response_msgs[-1]['content']
    blocks = match_code_block(content)
    if blocks:
        content = blocks[-1]
    
    new_chunks = parse_chunks_by_separators(content, [r'\S*', ])

    chunks.update(new_chunks)

    return chunks

def main(model, suggestion, context=None, chunks=None):
    template = load_jinja2_template(os.path.join(os.path.dirname(os.path.join(__file__)), "prompt.jinja2"))

    prompt = template.render(suggestion=suggestion, 
                             context=context,
                             chunks="\n\n".join([f"###{k}\n{v}" for k, v in chunks.items()]) if chunks else None)
    
    response_msgs = yield from chat([], prompt, model, parse_chat=True)

    updated_chunks = parser(response_msgs, chunks)

    return {'updated_chunks': updated_chunks, 'response_msgs':response_msgs}




