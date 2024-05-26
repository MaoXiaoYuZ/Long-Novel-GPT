import json
import os
from prompts.chat_utils import chat
from prompts.prompt_utils import load_jinja2_template, match_first_json_block
from promptflow.tracing import trace


@trace
def parser(response_msgs, text_chunks, topk):
    content = response_msgs[-1]['content']

    try:
        content = match_first_json_block(content)
        content_json = json.loads(content)
        if content_json and isinstance(topk_indexes := next(iter(content_json.values())), list):
                topk_indexes = [int(e) - 1 for e in topk_indexes[:topk]]
                if all(0 <= e < len(text_chunks) for e in topk_indexes):
                    return topk_indexes[:topk]
    except Exception as e:
        import traceback
        traceback.print_exc()
    
    return None


@trace
def main(model, question, text_chunks, topk):
    template = load_jinja2_template(os.path.join(os.path.dirname(os.path.join(__file__)), "prompt.jinja2"))

    prompt = template.render(references=text_chunks, 
                             question=question,
                             topk=topk)
    
    response_msgs = chat([], prompt, model, max_tokens=10 + topk * 4, response_json=True, parse_chat=True)

    topk_indexes = parser(response_msgs, text_chunks, topk)

    return {'topk_indexes': topk_indexes, 'response_msgs':response_msgs}
    


