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
        messages = self.get_chat_history(resume=False)

        messages.append({'role':'user', 'content': user_prompt})

        response_msgs = yield from self.chat(messages, response_json=False)
        response = response_msgs[-1]['content']
        
        self.text = response
        
        context_messsages = response_msgs
        if self.get_config('auto_compress_context'):
            context_messsages[-1]['content'] = "(已省略)"
        self.update_chat_history(context_messsages)
    
    def rewrite_text(self, human_feedback=None):
        if not human_feedback:
            human_feedback = "请从不符合逻辑，不符合人设，不符合大纲等方面进行反思。"
        
        messages = self.get_chat_history()

        input_text = '已省略，见上文。' if self.string_in_messages(self.text, messages) else self.text

        user_prompt = f"正文：{input_text}\n\n意见：{human_feedback}" + '\n\n' + \
"""接下来重写该章的正文。你需要根据意见进行分析，再重写。
你需要以如下JSON格式输出：
{
 "分析": "<进行分析>",
 "重写": "<这里重写该章正文>"
}
"""
        messages.append({'role':'user', 'content': user_prompt})

        response_msgs = yield from self.chat(messages, response_json=True)
        response = response_msgs[-1]['content']
        response_json = self.parse_json_block(response_msgs)
        
        self.text = response_json['重写']
        
        context_messsages = response_msgs
        if self.get_config('auto_compress_context'):
            context_messsages[-1]['content'] = "(已省略)"
        self.update_chat_history(context_messsages)
    
    def polish_text(self, human_feedback=None):
        if not human_feedback:
            human_feedback = "请从不符合逻辑，不符合人设，不符合大纲等方面进行反思。"

        messages = self.get_chat_history()

        input_text = '已省略，见上文。' if self.string_in_messages(self.text, messages) else self.text
        messages.append({"role": "user", "content": f"正文：{input_text}\n\n意见：{human_feedback}\n\n请根据意见对正文进行反思，再改进。"})
        response_msgs, corrected_chapter_detail = yield from self.prompt_polish(messages, self.text)

        self.text = corrected_chapter_detail

        context_messages = response_msgs
        if self.get_config('auto_compress_context'):
            context_messages[len(messages)-1]['content'] = f"意见：{human_feedback}\n\n请根据意见对正文进行反思，再改进。"
        if self.count_messages_length(context_messages[1:-4]) > self.get_config('chat_context_limit'):
            context_messages = yield from self.summary_messages(context_messages, [1, len(context_messages)-4])

        self.update_chat_history(context_messages)

        yield context_messages

