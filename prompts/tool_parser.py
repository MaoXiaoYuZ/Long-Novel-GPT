from promptflow.core import tool
from enum import Enum


class ResponseType(str, Enum):
    CONTENT = "content"
    SEPARATORS = "separators"
    CODEBLOCK = "codeblock"


import sys, os
root_path = os.path.abspath(os.path.join(os.path.abspath(__file__), "../.."))
if root_path not in sys.path:
    sys.path.append(root_path)

# The inputs section will change based on the arguments of the tool function, after you save the code
# Adding type to arguments and return value will help the system show the types properly
# Please update the function name/signature per need
@tool
def parse_response(response_msgs, response_type: Enum):
    from prompts.prompt_utils import parse_chunks_by_separators, match_code_block

    content = response_msgs[-1]['content']

    if response_type == ResponseType.CONTENT:
        return content
    elif response_type == ResponseType.CODEBLOCK:
        codeblock = match_code_block(content)
        
        if codeblock:
            return codeblock[-1]
        else:
            raise Exception("无法解析回答，未包含三引号代码块。")
        
    elif response_type == ResponseType.SEPARATORS:
        chunks = parse_chunks_by_separators(content, [r'\S*', ])
        return chunks
    else:
        raise Exception(f"无效的解析类型：{response_type}")
