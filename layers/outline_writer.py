import re
import json

from layers.writer import Writer

from prompts.检索参考材料 import prompt as retrieve_reference
from prompts.生成创作设定的意见 import prompt as generate_suggestion
from prompts.创作设定 import prompt as write_outline
from prompts.load_utils import run_prompt_by_func
from prompts.prompt_utils import parse_chunks_by_separators, construct_chunks_and_separators


class OutlineWriter(Writer):
    def __init__(self, output_path, model='gpt-4-1106-preview', sub_model="auto"):
        system_prompt = ""
        super().__init__(system_prompt, output_path, model, sub_model)

        self.outline = {}

        self.idea = ''

        self.load()

        self.set_config(write_outline = '现在需要你对小说设定进行创作。')
        self.set_config(refine_outline_setting = "之前输出的设定中还有很多可以改进的地方，请进行反思。")
    
    def init_by_idea(self, idea):
        self.idea = idea
    
    def get_input_context(self):
        return self.idea
    
    def get_output(self):
        return construct_chunks_and_separators({k:v for k, v in self.outline.items()})
    
    def set_output(self, outline: str):
        assert isinstance(outline, str)
        outline = parse_chunks_by_separators(outline, [r'\S*', ])
        self.outline = outline
    
    def get_attrs_needed_to_save(self):
        return [('outline', 'outline_content.json'), ('chat_history', 'outline_chat_history.json'), ('idea', 'idea.json')]

    def get_outline_content(self):
        return self.outline
    
    def update_outline(self, outline):
        self.outline = outline
    
    def generate_context(self, query, topk, chunks=None):
        topk = min(len(self.outline), topk)
        if not topk:
            return {}

        tuple_chunks = list(self.outline.items()) if chunks is None else list(chunks.items())
        text_chunks = [f"{e[0]}:{e[1]}".replace('\n', '').replace('\r', '') for e in tuple_chunks]

        if query:
            outputs = yield from run_prompt_by_func(retrieve_reference.main, 
                model=self.get_sub_model(),
                question=query,
                text_chunks=text_chunks,
                topk=topk,
                )
            
            topk_indexes = outputs['topk_indexes']

        if not query or not topk_indexes:
            topk_indexes = list(range(len(tuple_chunks)-1, len(self.outline)-1 - topk, -1))
        
        tuple_chunks = [tuple_chunks[i] for i in topk_indexes]
        return {k:v for k, v in tuple_chunks}
    
    def write_outline(self, human_feedback=None):
        yield []

        related_chunks = yield from self.generate_context(human_feedback, 5)
        
        outputs = yield from run_prompt_by_func(generate_suggestion.main,
            model=self.get_model(),
            instruction=human_feedback,
            context=self.get_input_context(),
            chunks=related_chunks,
            )
        
        refined_related_chunks = yield from self.generate_context(outputs['suggestion'], 3, related_chunks)
        
        outputs = yield from run_prompt_by_func(write_outline.main, 
            model=self.get_model(),
            suggestion=outputs['suggestion'],
            context=self.get_input_context(), 
            chunks=refined_related_chunks,
            )
        
        updated_chunks = outputs['updated_chunks']
        
        self.outline.update(updated_chunks)
