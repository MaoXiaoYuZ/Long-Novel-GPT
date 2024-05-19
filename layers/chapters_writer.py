import re
import json

from layers.writer import Writer

from prompts.load_utils import run_prompt
from prompts.prompt_utils import parse_chunks_by_separators, construct_chunks_and_separators

class ChaptersWriter(Writer):
    def __init__(self, output_path, model='gpt-4-1106-preview', sub_model="auto"):
        super().__init__('', output_path, model, sub_model)
        
        self.chapters = {}

        self.load()
    
    def init_by_outline_writer(self, outline_writer):
        self.outline_writer = outline_writer
    
    def get_input_context(self):
        return self.outline_writer.idea + '\n\n' + self.outline_writer.get_outline_content()
    
    def get_output(self):
        return construct_chunks_and_separators({k:v for k, v in self.chapters.items()})
    
    def set_output(self, chapters: str):
        assert isinstance(chapters, str)
        chapters = parse_chunks_by_separators(chapters, [r'\S*', ])
        self.chapters = chapters
    
    def update_output(self, chapters: str):
        assert isinstance(chapters, str)
        chapters = parse_chunks_by_separators(chapters, [r'\S*', ])
        self.chapters.update(chapters)
    
    def get_attrs_needed_to_save(self):
        return [('chapters' , 'chapters_content.json'), ('chat_history', 'chapters_chat_history.json')]
    
    def get_chapter_names(self):
        return list(self.chapters.keys())
    
    def get_chapter_content(self, chatper_name):
        return self.chapters[chatper_name]
    
    def init_chapters(self, human_feedback='', selected_text=''):
        # messages = self.get_chat_history()
        yield []

        context = self.get_input_context()
        
        outputs = yield from run_prompt(
            source="./prompts/生成创作章节的意见",
            chat_messages=[],
            model=self.get_model(),
            config=self.config,
            instruction=human_feedback,
            context=context,
            )

        outputs = yield from run_prompt(
            source="./prompts/创作章节",
            chat_messages=[],
            model=self.get_model(),
            config=self.config,
            text=selected_text,
            suggestion=outputs['suggestion'],
            context=context,
            )

        self.update_output(outputs['text'])

        # self.update_chat_history(context_messages)

    def construct_context(self, query, index):
        outputs = yield from run_prompt(
            source="./prompts/生成创作章节的上下文",
            chat_messages=[],
            model=self.get_sub_model(),
            config=self.config,
            text=query,
            context=index,
            )
        
        return outputs['knowledge']
    
    def rewrite_chatpers(self, human_feedback='', selected_text=''):
        # messages = self.get_chat_history()
        selected_text = selected_text.strip()
        if selected_text:
            assert selected_text in self.get_output(), '选定的用于重写的文本不存在'
        
        assert len(selected_text) > 0, '需要先选定要重写的内容'
        assert len(selected_text) > 7, '需要重写的内容过短'
        assert human_feedback, "意见不能为空！"

        yield []

        context = yield from self.construct_context(selected_text, self.get_input_context())

        outputs = yield from run_prompt(
            source="./prompts/生成重写章节的意见",
            chat_messages=[],
            model=self.get_model(),
            config=self.config,
            instruction=human_feedback,
            text=selected_text,
            context=context,
            )

        outputs = yield from run_prompt(
            source="./prompts/创作章节",
            chat_messages=[],
            model=self.get_model(),
            config=self.config,
            text=selected_text,
            suggestion=outputs['suggestion'],
            context=context,
            )
        
        self.set_output(self.get_output().replace(selected_text, outputs['text']))

        # context_messages = outputs['chat_messages']
        # if self.count_messages_length(context_messages[1:-2]) > self.get_config('chat_context_limit'):
        #     context_messages = yield from self.summary_messages(context_messages, [1, len(context_messages)-2])

        # self.update_chat_history(context_messages)
