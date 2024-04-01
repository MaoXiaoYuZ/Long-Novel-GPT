from promptflow import tool

# The inputs section will change based on the arguments of the tool function, after you save the code
# Adding type to arguments and return value will help the system show the types properly
# Please update the function name/signature per need
@tool
def parse_response(response_msgs, human_feedback, config):
    from prompts.prompt_utils import parse_first_json_block
    response_json = parse_first_json_block(response_msgs)
    chapters = {k: v['剧情'] for k, v in response_json.items() if isinstance(v, dict)}

    context_messages = response_msgs
    # if config['auto_compress_context']:
    #     context_messages[-2]['content'] = "现在开始创作分章剧情。要注意你创作的是章节剧情梗概，不是正文，不要描述过于细节的东西。\n" + f"意见：{human_feedback}"

    return {'chapters': chapters, 'chat_messages': context_messages}