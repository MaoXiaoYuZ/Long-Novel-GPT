from promptflow.core import tool

# The inputs section will change based on the arguments of the tool function, after you save the code
# Adding type to arguments and return value will help the system show the types properly
# Please update the function name/signature per need
@tool
def parse_response(response_msgs, human_feedback, config):
    from prompts.prompt_utils import match_code_block
    text = match_code_block(response_msgs[-1]['content'])[-1]

    context_messages = response_msgs

    return {'text': text, 'chat_messages': context_messages}