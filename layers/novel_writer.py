import re
import json

from layers.writer import ChatMessages, Writer

class NovelWriter(Writer):
    def __init__(self, output_path, model='gpt-4-1106-preview', sub_model="gpt-3.5-turbo-1106"):
        system_prompt = f'现在你是一个小说家，你需要根据大纲和章节剧情对某一章的正文进行创作。'
        super().__init__(system_prompt, output_path, model, sub_model)
        
        self.text = ''

        self.load()
    
    def init_by_outline_and_chapters_writer(self, outline_writer, volume_name, chapters_writer, chapter_name):
        context_chapter_names = self.get_context_elements_in_list(chapter_name, chapters_writer.get_chapter_names())
        chapters_context = chapters_writer.get_chapters_content(context_chapter_names)
        custom_system_prompt = f"\n\n下面是小说的大纲和分卷剧情:\n{outline_writer.get_outline_content(volume_names=[volume_name, ])}\n\n下面是小说中{volume_name}的分章剧情:\n{chapters_context}\n\n非常重要：你要创建的是{volume_name}的{chapter_name}的正文，其余卷或章作为上下文参考。"
        self.set_custom_system_prompt(custom_system_prompt)
    
    def get_attrs_needed_to_save(self):
        return [('text', 'novel_text.json'), ('chat_history', 'novel_chat_history.json')]

    def init_text(self, human_feedback=None):
        user_prompt = human_feedback + '\n\n' + \
"""接下来开始对该章的正文进行创作。你需要直接输出正文，不掺杂任何其他内容。
"""
        chat_id = 'init_text'
        
        messages = self.get_chat_history(chat_id, resume=False)

        messages.append({'role':'user', 'content': user_prompt})

        for response_msgs in self.chat(messages, response_json=False):
            yield response_msgs
        response = response_msgs[-1]['content']
        
        self.text = response
        
        context_messsages = response_msgs
        context_messsages[-1]['content'] = "(已省略)"
        self.chat_history[chat_id] = context_messsages
    
    def refine_text(self, human_feedback=None):
        if not human_feedback:
            human_feedback = "请从不符合逻辑，不符合人设，不符合大纲等方面进行反思。"

        chat_id = 'refine_text'
        messages = self.get_chat_history(chat_id, inherit='init_text')

        input_text = '已省略，见上文。' if self.string_in_messages(self.text, messages) else self.text
        messages.append({
            'role':'user', 
            'content': f"正文：{input_text}\n\n意见：{human_feedback}\n\n" + \
"""请根据意见对正文进行反思, 再改进。
请严格按照下面JSON格式输出：
{
 "反思": "<根据意见进行反思>",
 "修正一": {
  "问题分析": "<分析正文中存在的问题>",
  "参考文本": "<这里给出参考剧情中的句子或片段>",
  "改进方案": "<这里分析要如何改进>",
  "修正文本": "<这里输出改进后的文本>"
 },
 //列出更多修正，修正二，修正三，等
}
"""
        })

        for response_msgs in self.chat(messages, response_json=True):
            yield response_msgs
        response = response_msgs[-1]['content']
        response_json = json.loads(response)

        for response_revise_msgs in self.replace_text_by_review(self.text, response_json):
            yield response_revise_msgs

        corrected_chapter_detail = response_revise_msgs[-1]['content']

        self.text = corrected_chapter_detail

        context_messages = response_msgs[:-2]
        context_messages.append({'role':'user', 'content': f"意见：{human_feedback}\n\n请根据意见对正文进行反思。"})
        for v in response_json.values():
            if isinstance(v, dict):
                if '修正文本' in v and '参考文本' in v:
                    del v['修正文本']
                    del v['参考文本']
        context_messages.append({'role':'assistant', 'content': self.json_dumps(response_json)})
        context_messages.append({'role':'user', 'content': "很好，请根据反思内容，重新输出正文。"})
        context_messages.append({'role':'assistant', 'content': f"修改后的正文:\n(已省略)"})
        if self.count_messages_length(context_messages[1:-4]) > self.get_config('chat_context_limit'):
            for context_messages in self.summary_messages(context_messages, [1, len(context_messages)-4]):
                yield context_messages

        self.chat_history[chat_id] = context_messages

        yield context_messages
    
    def replace_text_by_review(self, text, review):
        context_messages = [
            {
                'role':'user', 
                'content': self.json_dumps({'输入文本': text}) + '\n\n' + f"意见：{review}"
            }]
        
        cost = 0
        for k, v in review.items():
            if isinstance(v, dict) and '修正文本' in v and '参考文本' in v:
                ref_text, replace_text = v['参考文本'], v['修正文本']
                if ref_text in text:
                    text = text.replace(ref_text, replace_text)
                else:
                    prompt = f"\n\n请问上述意见中：“{ref_text}”在原文中的对应句是什么，请以如下JSON格式回复。" + '{"对应句":"..."}'        
                    for i in range(3):
                        messages = [{'role':'user', 'content': context_messages[-1]['content'] + prompt}, ]
                        for response_msgs in self.chat(messages, model=self.get_sub_model(), response_json=True):
                            yield response_msgs
                        cost += response_msgs.cost
                        ref_text = json.loads(response_msgs[-1]['content'])['对应句']
                        if ref_text in text:
                            text = text.replace(ref_text, replace_text)
                            break
                    else:
                        print(f"ERROR:无法找到{ref_text}在原文中的对应句！")
        
        yield ChatMessages(context_messages + [{'role':'assistant', 'content': text}], model=self.get_sub_model(), cost=cost, currency_symbol='')

