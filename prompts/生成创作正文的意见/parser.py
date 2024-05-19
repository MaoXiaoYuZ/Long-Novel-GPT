from promptflow.core import tool


@tool
def parse_response(response_msgs):
    from prompts.prompt_utils import parse_chunks_by_separators
    content = response_msgs[-1]['content']

    chunks = parse_chunks_by_separators(content, [r'\S*', ])
    if "意见" in chunks:
        return chunks["意见"]
    else:
        return content
