def parse_content(response_msgs):
    return response_msgs[-1]['content']


def parse_last_code_block(response_msgs):
    from prompts.prompt_utils import match_code_block
    content = response_msgs.response
    blocks = match_code_block(content)
    if blocks:
        content = blocks[-1]
    return content

def parse_named_chunk(response_msgs, name):
    from prompts.prompt_utils import parse_chunks_by_separators
    content = response_msgs[-1]['content']

    chunks = parse_chunks_by_separators(content, [r'\S*', ])
    if name in chunks:
        return chunks[name]
    else:
        return content
