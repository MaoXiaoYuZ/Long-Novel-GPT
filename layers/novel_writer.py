from collections import defaultdict
import re
import json

from layers.writer import ChatMessages, Writer

class NovelWriter(Writer):
    def __init__(self, output_path, model='gpt-4-1106-preview', sub_model="gpt-3.5-turbo-1106"):
        system_prompt = f'现在你是一个小说家，你需要根据大纲和章节剧情对某一章的正文进行创作。'
        super().__init__(system_prompt, output_path, model, sub_model)
        
        self.chapter2text = {}
        self.cur_chapter_name = None

        self.load()
    
    def init_by_outline_and_chapters_writer(self, outline_writer, chapters_writer):
        self.outline_writer = outline_writer
        self.chapters_writer = chapters_writer
    
    def set_cur_chapter_name(self, chapter_name):
        self.cur_chapter_name = chapter_name

    def get_input_context(self):
        input_context = self.outline_writer.get_input_context()
        input_context += '\n\n' + self.outline_writer.get_outline_content()
        if self.cur_chapter_name:
            input_context += '\n\n' + self.chapters_writer.get_chapters_content(self.cur_chapter_name)
        return input_context
    
    def get_output(self):
        chapter_name = self.cur_chapter_name if self.cur_chapter_name else '默认章节名'
        return self.chapter2text[chapter_name] if chapter_name in self.chapter2text else ''
    
    def set_output(self, chapter_text):
        chapter_name = self.cur_chapter_name if self.cur_chapter_name else '默认章节名'
        self.chapter2text[chapter_name] = chapter_text

    def get_attrs_needed_to_save(self):
        return [('chapter2text', 'chapter2text.json'), ('chat_history', 'novel_chat_history.json')]

    def init_text(self, human_feedback=None, selected_text=None):
        user_prompt = human_feedback + '\n\n' + \
"""接下来开始对该章的正文进行创作。你需要直接输出正文，不掺杂任何其他内容。
"""
        messages = self.get_chat_history()

        messages.append({'role':'user', 'content': user_prompt})
        if 'chatgpt' in self.get_model() and messages[0]['role'] == 'system':
            messages[-1]['content'] = messages[0]['content'] + '\n\n' + messages[-1]['content']
            
        response_msgs = yield from self.chat(messages, response_json=False)
        response = response_msgs[-1]['content']
        
        self.set_output(response)
        
        context_messsages = response_msgs
        if self.get_config('auto_compress_context'):
            context_messsages[-1]['content'] = "(已省略)"
        self.update_chat_history(context_messsages)
    
    def rewrite_text(self, human_feedback=None, selected_text=None):
        if not human_feedback:
            human_feedback = "请从不符合逻辑，不符合人设，不符合大纲等方面进行反思。"
        
        messages = self.get_chat_history()

        input_text = '已省略，见上文。' if self.string_in_messages(self.get_output(), messages) else self.get_output()

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
        
        self.set_output(response_json['重写'])
        
        context_messsages = response_msgs
        if self.get_config('auto_compress_context'):
            context_messsages[-1]['content'] = "(已省略)"
        self.update_chat_history(context_messsages)
    
    def polish_text(self, human_feedback=None, selected_text=None):
        if not human_feedback:
            human_feedback = "请从不符合逻辑，不符合人设，不符合大纲等方面进行反思。"

        messages = self.get_chat_history()

        input_text = '已省略，见上文。' if self.string_in_messages(self.get_output(), messages) else self.get_output()
        messages.append({"role": "user", "content": f"正文：{input_text}\n\n意见：{human_feedback}\n\n请根据意见对正文进行反思，再改进。"})
        response_msgs, corrected_chapter_detail = yield from self.prompt_polish(messages, self.get_output())

        self.set_output(corrected_chapter_detail)

        context_messages = response_msgs
        if self.get_config('auto_compress_context'):
            context_messages[len(messages)-1]['content'] = f"意见：{human_feedback}\n\n请根据意见对正文进行反思，再改进。"
        if self.count_messages_length(context_messages[1:-4]) > self.get_config('chat_context_limit'):
            context_messages = yield from self.summary_messages(context_messages, [1, len(context_messages)-4])

        self.update_chat_history(context_messages)

        yield context_messages

