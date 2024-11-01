import re
import numpy as np
import json
import os
from glob import glob
from itertools import chain
from collections import Counter

from llm_api.chat_messages import ChatMessages
from llm_api.openai_api import stream_chat_with_gpt
from llm_api.baidu_api import stream_chat_with_wenxin
from llm_api.openai_api import stream_chat_with_chatgpt


class Writer:
    def __init__(self, system_prompt, output_path, model, sub_model):
        self.output_path = output_path

        self.config = {'chat_context_limit': 2000, 'auto_compress_context': True, }
        
        self.system_prompt = system_prompt
        self.set_model(model, sub_model)

        self.chat_history = {
            'system_messages': [{'role':'system', 'content': system_prompt}],
            }
    
    def get_input_context(self) -> str:
        raise NotImplementedError
    
    def get_output(self) -> str:
        raise NotImplementedError
    
    def set_output(self, e):
        raise NotImplementedError
    
    def get_chat_history(self, chat_id='main_chat', resume=True, inherit='system_messages'):
        if not resume or (chat_id not in self.chat_history):
            if inherit == 'system_messages':
                return [{'role':'system', 'content': self.chat_history['system_messages'][0]['content'] + self.get_input_context()}, ]
            else:
                return list(self.chat_history[inherit])
        else:
            return list(self.chat_history[chat_id])
    
    def update_chat_history(self, messages, chat_id='main_chat'):
        self.chat_history[chat_id] = messages
    
    def has_chat_history(self, chat_id='main_chat'):
        return chat_id in self.chat_history
    
    def set_meta_info(self, meta_info):
        self.meta_info = meta_info
    
    def set_model(self, model, sub_model='auto'):
        if sub_model == 'auto':
            if 'gpt' in model:
                sub_model = 'gpt-3.5-turbo-1106'
            elif 'ERNIE' in model:
                sub_model = 'ERNIE-Bot'
            elif 'chatgpt' in model:
                sub_model = 'gpt-3.5-turbo-1106'
        self.set_config(model=model, sub_model=sub_model)
    
    def get_model(self):
        return self.get_config('model')
    
    def get_sub_model(self):
        return self.get_config('sub_model')
    
    def set_config(self, **kwargs):
        self.config.update(**kwargs)
    
    def get_config(self, k):
        if k == 'chat_context_limit' and 'chatgpt' in self.get_model():
            return 100_000_000  # chatgpt不限制context长度
        if k == 'auto_compress_context' and 'chatgpt' in self.get_model():
            return False  # chatgpt不自动压缩context
        return self.config[k]
    
    def print_messages(self, messages):
        for msg in messages:
            print(msg['role'] + ":")
            print(msg['content'])
    
    def count_messages_length(self, messages):
        return messages.count_message_tokens()
    
    def string_in_messages(self, string, messages):
        return any([string in msg['content'] for msg in messages])
    
    def comment_duplicate_inputs(self, inputs, messages):
        comment = "...(见上文)..."
        if isinstance(inputs, str):
            if len(inputs) > 20 and self.string_in_messages(inputs, messages):
                return comment
            else:
                return inputs

        new_inputs = {}
        for k, v in inputs.items():
            if isinstance(v, str):
                if len(v) > 20 and self.string_in_messages(v, messages):
                    new_inputs[k] = comment
                else:
                    new_inputs[k] = v
            elif isinstance(v, dict):
                new_inputs[k] = self.comment_duplicate_inputs(v, messages)
            elif isinstance(v, list):
                new_inputs[k] = [self.comment_duplicate_inputs(vi, messages) for vi in v]
            else:
                raise NotImplementedError('comment_duplicate_inputs只支持str和dict类型的值！')
        return new_inputs
    
    def get_context_elements_in_list(self, ele, l, context_length=1):
        index = l.index(ele)
        return l[max(0, index-context_length):min(len(l), index+context_length+1)]

    def chat(self, messages, model=None, max_tokens=4000, response_json=False, n=1):
        if model is None: model = self.get_model()
        if 'chatgpt' in model:
            ret = yield from stream_chat_with_chatgpt(messages, model=model, max_tokens=max_tokens, response_json=response_json, n=n)
        elif 'gpt' in model:
            ret = yield from stream_chat_with_gpt(messages, model=model, max_tokens=max_tokens, response_json=response_json, n=n)
        elif 'ERNIE' in model:
            ret = yield from stream_chat_with_wenxin(messages, model=model, response_json=response_json)
        else:
            raise NotImplementedError(f"未知的model:{model}！")
        return ret

    def function_chat(self, messages, tools, model=None, max_tokens=4000):
        if model is None: model = self.get_model()
        if 'gpt' in model:
            messages, content, function_calls = yield from stream_function_calling_with_gpt(messages, tools, model=model, max_tokens=max_tokens)
            return messages, content, function_calls
        elif 'ERNIE' in model:
            raise NotImplementedError('此功能暂不支持文心模型！')

    def json_dumps(self, json_object):
        return json.dumps(json_object, ensure_ascii=False, indent=1)
    
    def json_save(self, json_object, output_file):
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(self.json_dumps(json_object))
    
    def json_load(self, input_file):
        with open(input_file, 'r', encoding='utf-8') as f:
            return json.load(f)
        
    def parse_json_block(self, response_msgs: ChatMessages):
        model = response_msgs.model
        assert response_msgs[-1]['role'] == 'assistant'
        if 'chatgpt' in model:
            return json.loads(match_first_json_block(response_msgs[-1]['content']))
        else:
            return json.loads(response_msgs[-1]['content'])
        
    def get_attrs_needed_to_save(self):
        raise NotImplementedError()
    
    def save(self, output_path=None):
        attrs = self.get_attrs_needed_to_save()
        if output_path is None: output_path = self.output_path
        os.makedirs(output_path, exist_ok=True)
        for attr, filename in attrs:
            attr_json_file = os.path.join(output_path, filename)
            self.json_save(getattr(self, attr), attr_json_file)
    
    def load(self, output_path=None):
        if output_path is None: output_path = self.output_path
        attrs = self.get_attrs_needed_to_save()
        for attr, filename in attrs:
            attr_json_file = os.path.join(output_path, filename)
            if os.path.exists(attr_json_file):
                setattr(self, attr, self.json_load(attr_json_file))
    
    def discuss(self, prompt):
        messages = self.get_chat_history()
        messages.append({'role':'user', 'content': prompt})  
        response_msgs = yield from self.chat(messages, response_json=False)
        context_messages = response_msgs
        self.update_chat_history(context_messages)
        yield context_messages
    
    def summary_messages(self, messages, range=None):
        if range is None: range = [0, len(messages)]

        prev_messages = messages[:range[0]]
        next_messages = messages[range[1]:]
        messages = messages[range[0]:range[1]]

        prompt =  \
"""请总结上述我们的所有对话在讨论什么，各自的观点是什么，达成什么共识，得出了什么结论，请进行梳理，整理成'对话总结'，用于我们之后的对话。
如果在总结中你发现上述对话的部分内容已经有'对话总结'，那么可以在它的基础上进行更新，并输出更新后的'对话总结'。
你需要按下面JSON形式输出'对话总结'：
{
 "讨论": "<描述我们的对话讨论的内容>",
 "共识": [
  "<在讨论中提出的一些重要的观点/共识/结论>",
  //列出更多重要观点/共识/结论
 ]
}
"""
        messages = messages + [{'role': 'user', 'content': prompt}, ]

        for response_msgs in self.chat(messages, model=self.get_model(), response_json=True):
            #yield prev_messages + response_msgs + next_messages
            yield response_msgs

        context_messages = [{'role': 'user', 'content': '...(已省略，见之后总结)...'}, {'role': 'assistant', 'content': '...(已省略，见之后总结)...'}]
        context_messages.append({'role': 'user', 'content': prompt})
        context_messages.append(response_msgs[-1])

        return prev_messages + context_messages + next_messages
    
    def vote(self, messages, n, response_json=None):
        for response_msgs in self.chat(messages, model=self.get_sub_model(), response_json=response_json, n=n):
            if n > 1:
                new_response_msgs = response_msgs[:-1] + [{'role': 'user', 'content': response_msgs[-1]['content'][0]}]
                new_response_msgs.cost = response_msgs.cost
                yield new_response_msgs
            else:
                yield response_msgs

        if n > 1:
            common_content = Counter(response_msgs[-1]['content']).most_common(1)[0][0]
            response_msgs[-1]['content'] = common_content

        return response_msgs
    
    def prompt_polish(self, messages, text):
        assert messages[-1]['role'] == 'user'

        prompt = messages[-1]['content']
        messages = messages[:-1] + [
            {
            'role':'user', 
            'content': prompt + "\n\n" + \
"""请严格按照下面JSON格式输出：
{
 "思考": "<进行思考>",
 "修正一": {
  "问题分析": "<分析存在的问题>",
  "改进方式": "<填 在参考文本前插入/在参考文本后插入/替换参考文本>",
  "参考文本": "<这里给出参考的句子或片段>",
  "改进方案": "<这里分析要如何改进>",
  "修正文本": "<这里输出需要插入/替换的文本>"
 },
 //列出更多修正，修正二，修正三，等
}
"""
        }]

        response_msgs = yield from self.chat(messages, response_json=True)
        response_json = self.parse_json_block(response_msgs)

        response_parser_msgs, replaced_text  = yield from self._prompt_polish_parser(text, response_json)

        context_messages = response_msgs
        if self.get_config('auto_compress_context'):
            context_messages = response_msgs[:-1]
            context_messages[-1]['content'] = prompt
            for v in response_json.values():
                if isinstance(v, dict):
                    for k in ['修正文本', '参考文本', '改进方式']:
                        if k in v:
                            del v[k]
            context_messages.append({'role':'assistant', 'content': self.json_dumps(response_json) + "\n\n以下是改进后的文本：（已省略）"})

        yield context_messages

        return context_messages, replaced_text
    
    def _prompt_polish_parser(self, text, response):
        context_messages = [
            {
                'role':'user', 
                'content': self.json_dumps({'输入文本': text}) + '\n\n' + f"意见：{response}"
            }]
        
        def replace(replace_method, reference_text, insert_text):
            nonlocal text
            if replace_method == '在参考文本前插入':
                text = text.replace(reference_text, insert_text + reference_text)
            elif replace_method == '在参考文本后插入':
                text = text.replace(reference_text, reference_text + insert_text)
            elif replace_method == '替换参考文本':
                text = text.replace(reference_text, insert_text)
            else:
                print(f"ERROR:无法识别的改进方式{replace_method}！")
        
        cost = 0
        for k, v in response.items():
            if isinstance(v, dict) and '修正文本' in v and '参考文本' in v and '改进方式' in v:
                ref_text, replace_text, replace_method = v['参考文本'], v['修正文本'], v['改进方式']
                if ref_text in text:
                    replace(replace_method, ref_text, replace_text)
                else:
                    prompt = f"\n\n请问上述意见中：“{ref_text}”在原文中的对应句是什么，请以如下JSON格式回复。" + '{"对应句":"..."}'        
                    for i in range(3):
                        messages = [{'role':'user', 'content': context_messages[-1]['content'] + prompt}, ]
                        response_msgs = yield from self.chat(messages, model=self.get_sub_model(), response_json=True)
                        cost += response_msgs.cost
                        ref_text = self.parse_json_block(response_msgs)['对应句']
                        if ref_text in text:
                            replace(replace_method, ref_text, replace_text)
                            break
                    else:
                        print(f"ERROR:无法找到{ref_text}在原文中的对应句！")
        
        return ChatMessages(context_messages + [{'role':'assistant', 'content': text}], model=self.get_sub_model(), cost=cost, currency_symbol=''), text


