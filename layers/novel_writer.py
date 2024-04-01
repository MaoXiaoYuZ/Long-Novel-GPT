from collections import defaultdict
import re
import json

from layers.writer import ChatMessages, Writer
from prompts.load_utils import run_prompt

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
    
    def get_cur_chapter_name(self):
        return self.cur_chapter_name

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
    
    def init_text(self, human_feedback='', selected_text=''):
        yield []

        feedback = f"{self.get_input_context()}\n\n{human_feedback}"
        
        outputs = yield from run_prompt(
            source="./prompts/新建正文/默认",
            chat_messages=[],
            feedback=feedback,
            model=self.get_model(),
            config=self.config
            )

        self.set_output(outputs['text'])
    
    def rewrite_text(self, human_feedback='', selected_text=''):
        yield []

        outputs = yield from run_prompt(
            source="./prompts/重写正文/默认",
            chat_messages=[],
            model=self.get_model(),
            config=self.config,
            text=selected_text,
            feedback=human_feedback,
            )
        
        self.set_output(self.get_output().replace(selected_text, outputs['text']))

    def polish_text(self, human_feedback='', selected_text=''):
        assert selected_text in self.get_output(), f"选定的文本未找到：{selected_text}"
        
        yield []

        prompt = yield from run_prompt(
            source="./prompts/润色正文/默认",
            chat_messages=[],
            model=self.get_model(),
            config=self.config,
            text=selected_text,
            feedback=human_feedback
            )
        prompt = prompt['prompt']
        
        outputs = yield from run_prompt(
            source="./prompts/polish",
            chat_messages=[],
            context=prompt,
            model=self.get_model(),
            config=self.config,
            text=selected_text,
            )
        
        self.set_output(self.get_output().replace(selected_text, outputs['text']))