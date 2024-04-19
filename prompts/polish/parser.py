from promptflow.core import tool

from difflib import SequenceMatcher

from prompts.prompt_utils import match_chunk_span_in_text

# The inputs section will change based on the arguments of the tool function, after you save the code
# Adding type to arguments and return value will help the system show the types properly
# Please update the function name/signature per need
@tool
def parse_response(response_msgs, context, text, config):
    from prompts.prompt_utils import parse_first_json_block,  json_dumps

    response_json = parse_first_json_block(response_msgs)

    replaced_text  = _prompt_polish_parser(text, response_json)

    context_messages = response_msgs
    if config['auto_compress_context']:
        context_messages = response_msgs[:-1]
        context_messages[-1]['content'] = context
        for v in response_json.values():
            if isinstance(v, dict):
                for k in ['修正文本', '参考文本', '改进方式']:
                    if k in v:
                        del v[k]
        context_messages.append({'role':'assistant', 'content': json_dumps(response_json) + "\n\n以下是改进后的文本：（已省略）"})

    return {'chat_messages': context_messages, 'text':replaced_text}


def _prompt_polish_parser(text, response):
    def modify_text(replace_method, insert_text, l, r):
        nonlocal text
        if replace_method == '在参考文本前插入':
            text = text[:l] + insert_text + text[l:]
        elif replace_method == '在参考文本后插入':
            text = text[:r] + insert_text + text[r:]
        elif replace_method == '替换参考文本':
            text = text[:l] + insert_text + text[r:]
        else:
            print(f"ERROR:无法识别的改进方式{replace_method}！")

    MIN_MATCH_RATIO = 0.75 

    for k, v in response.items():
        if isinstance(v, dict) and '修正文本' in v and '参考文本' in v and '改进方式' in v:
            ref_text, replace_text, replace_method = v['参考文本'], v['修正文本'], v['改进方式']
            l, r = match_chunk_span_in_text(ref_text, text)
            match_ratio =  len(ref_text) / (r - l)
            
            if match_ratio >= MIN_MATCH_RATIO:
                modify_text(replace_method, replace_text, l, r)
            else:
                print(f"未找到足够相似的文本匹配项。最佳匹配率: {match_ratio}")

    return text


