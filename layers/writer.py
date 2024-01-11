import re
import numpy as np
import json
import os
from glob import glob
from itertools import chain
from collections import Counter

# import sys
# sys.path.append(os.path.abspath(os.path.join(__file__, '../..')))   

from llm_api.openai_api import num_tokens_from_messages, count_gpt_api_cost, stream_chat_with_gpt

class ChatMessages(list):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = kwargs['model'] if 'model' in kwargs else None
        self.cost = kwargs['cost'] if 'cost' in kwargs else None
    
    def __getitem__(self, index):
        result = super().__getitem__(index)
        if isinstance(index, slice):
            return ChatMessages(result, model=self.model, cost=self.cost)
        return result
    
    def __add__(self, other):
        if isinstance(other, list):
            return ChatMessages(super().__add__(other), model=self.model, cost=self.cost)
        return NotImplemented 


class Writer:
    def __init__(self, system_prompt, output_path, model, sub_model):
        self.output_path = output_path

        self.config = {'chat_context_limit': 2000}
        
        self.system_prompt = system_prompt
        self.set_model(model, sub_model)

        self.chat_history = {
            'system_messages': [{'role':'system', 'content': system_prompt}],
            'custom_system_prompt': [{'role':'system', 'content': ''}],
            }
    
    def set_custom_system_prompt(self, custom_system_prompt):
        self.chat_history['custom_system_prompt'][0]['content'] = custom_system_prompt
    
    def get_custom_system_prompt(self):
        return self.chat_history['custom_system_prompt'][0]['content']
    
    def get_chat_history(self, chat_id, resume=True, inherit='system_messages'):
        if not resume or (chat_id not in self.chat_history):
            if inherit == 'system_messages':
                return [{'role':'system', 'content': self.chat_history['system_messages'][0]['content'] + self.get_custom_system_prompt()}, ]
            else:
                return list(self.chat_history[inherit])
        else:
            return list(self.chat_history[chat_id])
    
    def has_chat_history(self, chat_id):
        return chat_id in self.chat_history
    
    def set_meta_info(self, meta_info):
        self.meta_info = meta_info
    
    def set_model(self, model, sub_model='gpt-3.5-turbo-1106'):
        self.set_config(model=model, sub_model=sub_model)
    
    def get_model(self):
        return self.get_config('model')
    
    def get_sub_model(self):
        return self.get_config('sub_model')
    
    def set_config(self, **kwargs):
        self.config.update(**kwargs)
    
    def get_config(self, k):
        return self.config[k]
    
    def print_messages(self, messages):
        for msg in messages:
            print(msg['role'] + ":")
            print(msg['content'])
    
    def count_messages_length(self, messages):
        return sum([len(msg['content']) for msg in messages])
    
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
    
    def count_context_cost(self, messages, model):
        context_tokens = num_tokens_from_messages(messages)
        return count_gpt_api_cost(model, context_tokens, 0)
    
    def count_completion_cost(self, completion, model):
        if not isinstance(completion, list):
            completion = [completion, ]
            
        completion_tokens = num_tokens_from_messages([{'role': 'assistant', 'content': completion[0]}, ]) * len(completion) # 快速估计

        return count_gpt_api_cost(model, 0, completion_tokens)
    
    def chat(self, messages, model=None, max_tokens=4000, response_format={ "type": "json_object" }, n=1):
        if model is None: model = self.get_model()
        messages = ChatMessages(messages, model=model)
        context_cost = self.count_context_cost(messages, model)
        messages.cost = context_cost
        yield messages
        messages.append({'role': 'assistant', 'content': ''})
        for response in stream_chat_with_gpt(messages, model=model, max_tokens=max_tokens, response_format=response_format, n=n):
            messages[-1]['content'] = response
            messages.cost = context_cost + self.count_completion_cost(response, model=model)
            yield messages
    
    def json_dumps(self, json_object):
        return json.dumps(json_object, ensure_ascii=False, indent=1)
    
    def json_save(self, json_object, output_file):
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(self.json_dumps(json_object))
    
    def json_load(self, input_file):
        with open(input_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
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

        for response_msgs in self.chat(messages, model=self.get_model(), response_format={ "type": "json_object"}):
            #yield prev_messages + response_msgs + next_messages
            yield response_msgs

        context_messages = [{'role': 'user', 'content': '...(已省略，见之后总结)...'}, {'role': 'assistant', 'content': '...(已省略，见之后总结)...'}]
        context_messages.append({'role': 'user', 'content': prompt})
        context_messages.append(response_msgs[-1])

        yield prev_messages + context_messages + next_messages
    
    def vote(self, messages, n, response_format=None):
        for response_msgs in self.chat(messages, model=self.get_sub_model(), response_format=response_format, n=n):
            if n > 1:
                new_response_msgs = response_msgs[:-1] + [{'role': 'user', 'content': response_msgs[-1]['content'][0]}]
                new_response_msgs.cost = response_msgs.cost
                yield new_response_msgs
            else:
                yield response_msgs

        if n > 1:
            common_content = Counter(response_msgs[-1]['content']).most_common(1)[0][0]
            response_msgs[-1]['content'] = common_content

        yield response_msgs



if __name__ == '__main__':
    writer = Writer('我是系统提示', 'output/test', 'gpt-3.5-turbo-1106', 'gpt-3.5-turbo-1106')