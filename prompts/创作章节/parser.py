from promptflow.core import tool


@tool
def parse_response(response_msgs):
    from prompts.prompt_utils import match_code_block
    content = response_msgs[-1]['content']
    blocks = match_code_block(content)
    if blocks:
        content = blocks[-1]
    return content
