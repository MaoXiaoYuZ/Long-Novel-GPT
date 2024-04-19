import re
import json

from layers.writer import Writer

from prompts.load_utils import run_prompt
from prompts.prompt_utils import parse_chunks_by_separators, construct_chunks_and_separators

class ChaptersWriter(Writer):
    def __init__(self, output_path, model='gpt-4-1106-preview', sub_model="gpt-3.5-turbo-1106"):
        system_prompt = "我会给你小说的大纲，需要你创作分章剧情。你需要遵从我的指令，让我们一起一步步进行章节剧情的创作。首先，我们会创作分章剧情，然后再对每章的剧情进行扩充。同时，对于你创作的剧情，我会要求你反思或根据我给出的意见进行修改。"
        super().__init__(system_prompt, output_path, model, sub_model)
        
        self.chapters = {}

        self.load()
    
    def init_by_outline_writer(self, outline_writer):
        self.outline_writer = outline_writer
    
    def get_input_context(self):
        return self.outline_writer.idea + '\n\n' + self.outline_writer.get_outline_content()
    
    def get_output(self):
        return self.get_chapters_content()
    
    def set_output(self, chapters: str):
        assert isinstance(chapters, str)
        chapters = parse_chunks_by_separators(chapters, [r'\S*', ])
        self.chapters = chapters
    
    def get_attrs_needed_to_save(self):
        return [('chapters' , 'chapters_content.json'), ('chat_history', 'chapters_chat_history.json')]
    
    def get_chapter_names(self):
        return list(self.chapters.keys())
    
    def get_chapters_content(self, chatper_names=None):
        if chatper_names is None:
            chatper_names = self.get_chapter_names()
        return construct_chunks_and_separators({k:v for k, v in self.chapters.items() if k in chatper_names})

    def init_chapters(self, human_feedback='', selected_text=''):
        # messages = self.get_chat_history()
        yield []

        feedback = f"{self.get_input_context()}\n\n{human_feedback}"
        
        outputs = yield from run_prompt(
            source="./prompts/新建章节",
            chat_messages=[],
            feedback=feedback,
            model=self.get_model(),
            config=self.config
            )

        self.chapters, context_messages = outputs['chapters'], outputs['chat_messages']
        
        # self.update_chat_history(context_messages)

    # def construct_context(self, chapter_name, human_feedback, selected_text):
    #     messages = self.get_chat_history()

    #     context_chapter_names = self.get_context_elements_in_list(chapter_name, self.get_chapter_names(), context_length=1)
    #     input_chapters = self.comment_duplicate_inputs({k:v for k,v in self.chapters.items() if k in context_chapter_names}, messages)
    #     input_chapters = construct_chunks_and_separators(input_chapters)

    #     context = f"### 章节剧情：\n{input_chapters}\n\n"
    #     if human_feedback:
    #         context +=  f"### 反馈意见：\n{human_feedback}\n\n"

    #     if selected_text:
    #         assert selected_text in self.chapters[chapter_name], f'选定的用于润色的文本和需要重写的章节<{chapter_name}>不符'
    #         assert len(selected_text) > 7, '需要润色的内容过短'
    #     else:
    #         selected_text = self.chapters[chapter_name]

    #     return selected_text
    
    def rewrite_chatpers(self, chapter_name, human_feedback='', selected_text=''):
        # messages = self.get_chat_history()
        selected_text = selected_text.strip()
        if selected_text:
            assert selected_text in self.chapters[chapter_name], f'选定的用于重写的文本和需要重写的章节<{chapter_name}>不符'
            assert len(selected_text) > 7, '需要重写的内容过短'
        else:
            selected_text = self.chapters[chapter_name]

        assert human_feedback, "意见不能为空！"

        yield []

        outputs = yield from run_prompt(
            source="./prompts/生成重写章节的上下文",
            chat_messages=[],
            model=self.get_sub_model(),
            config=self.config,
            text=selected_text,
            context=self.get_input_context(),
            )

        outputs = yield from run_prompt(
            source="./prompts/生成重写章节的意见",
            chat_messages=[],
            model=self.get_model(),
            config=self.config,
            question=human_feedback,
            text=selected_text,
            context=outputs['knowledge'],
            )

        outputs = yield from run_prompt(
            source="./prompts/重写章节",
            chat_messages=[],
            model=self.get_model(),
            config=self.config,
            text=selected_text,
            feedback=outputs['feedback'],
            )
        
        self.chapters[chapter_name] = self.chapters[chapter_name].replace(selected_text, outputs['text'])

        # context_messages = outputs['chat_messages']
        # if self.count_messages_length(context_messages[1:-2]) > self.get_config('chat_context_limit'):
        #     context_messages = yield from self.summary_messages(context_messages, [1, len(context_messages)-2])

        # self.update_chat_history(context_messages)
