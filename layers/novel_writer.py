from collections import defaultdict
import math
import re
import json

from layers.writer import ChatMessages, Writer
from prompts.load_utils import run_prompt, run_prompt_no_echo
from layers.layer_utils import split_text_into_paragraphs, detect_max_edit_span

import numpy as np
from itertools import chain 
import bisect

class NovelWriter(Writer):
    def __init__(self, output_path, model='gpt-4-1106-preview', sub_model="auto"):
        system_prompt = ''
        super().__init__(system_prompt, output_path, model, sub_model)
        
        self.chapter2text = {}
        self.cur_chapter_name = None
        self.plot_text_pairs = []

        self.load()
    
    def init_by_outline_and_chapters_writer(self, outline_writer, chapters_writer):
        self.outline_writer = outline_writer
        self.chapters_writer = chapters_writer
    
    def set_cur_chapter_name(self, chapter_name):
        self.cur_chapter_name = chapter_name
    
    def get_cur_chapter_name(self):
        return self.cur_chapter_name

    def get_input_context(self):
        if self.cur_chapter_name:
            input_context = f"### {self.cur_chapter_name} 剧情\n"
            input_context += self.chapters_writer.get_chapter_content(self.cur_chapter_name)
        else:
            input_context = ""
            # input_context += self.outline_writer.get_input_context()
            # input_context += '\n\n' + self.outline_writer.get_outline_content()

        return input_context
    
    # update_plot(plot和text之间映射关系的建立)是独立于update_text的。
    # 也就是说，update_plot不依赖于记录每次text的更改，自己会维护一个记录。
    # 这样避免了update_text时引入更多的操作，造成更多开销。
    # 也便于实现lazy_update, 在查询某段text对应的plot时才更新plot和text映射。
    def update_plot(self):
        plot = self.chapters_writer.get_chapter_content(self.cur_chapter_name)
        text = self.get_output()

        if not text.strip():
            return

        if self.plot_text_pairs:
            plot_chunks, text_chunks = [e[0] for e in self.plot_text_pairs], [e[1] for e in self.plot_text_pairs]
            concat_plot, concat_text = "".join(plot_chunks), "".join(chain.from_iterable(text_chunks))
            if concat_plot == plot and concat_text == text:
                pass
            elif concat_plot != plot and concat_text != text:
                self._update_plot(0, len(plot_chunks), new_plot_chunks=split_text_into_paragraphs(plot), new_text_chunks=split_text_into_paragraphs(text))
            elif concat_plot != plot:
                new_plot_chunks = split_text_into_paragraphs(plot)
                l, r = detect_max_edit_span(plot_chunks, new_plot_chunks)
                self._update_plot(l, len(plot_chunks)+r, new_plot_chunks=new_plot_chunks[l: len(new_plot_chunks)+r])
            else:
                new_text_chunks = split_text_into_paragraphs(text)
                l, r = detect_max_edit_span(list(chain.from_iterable(text_chunks)), new_text_chunks)
                cumsum = np.cumsum([0, ] + [len(e) for e in text_chunks]).tolist()
                plot_l, plot_r = bisect.bisect_right(cumsum, l) - 1, bisect.bisect_right(cumsum, cumsum[-1] + r)
                text_l, text_r = cumsum[plot_l], cumsum[plot_r]

                self._update_plot(plot_l, plot_r, new_text_chunks=new_text_chunks[text_l: len(new_text_chunks) - (cumsum[-1] - text_r)])
        else:
            plot_chunks, text_chunks =split_text_into_paragraphs(plot), split_text_into_paragraphs(text)
            self.plot_text_pairs = [[] for _ in range(len(plot_chunks))]
            self._update_plot(0, len(plot_chunks), new_plot_chunks=plot_chunks, new_text_chunks=text_chunks)

    
    def _update_plot(self, l, r, new_plot_chunks=None, new_text_chunks=None):
        if new_plot_chunks is None:
            new_plot_chunks = [self.plot_text_pairs[i][0] for i in range(l, r)]
        
        if new_text_chunks is None:
            new_text_chunks = list(chain.from_iterable([self.plot_text_pairs[i][1] for i in range(l, r)]))
        
        assert r - l > 0
        if r - l == 1:
            self.plot_text_pairs[l] = (new_plot_chunks[0], (new_text_chunks))
        else:
            output = run_prompt_no_echo(
                source="./prompts/对齐剧情和正文",
                chat_messages=[],
                model=self.get_sub_model(),
                config=self.config,
                plot_chunks=new_plot_chunks,
                text_chunks=new_text_chunks
                )
            
            plot2text = output['plot2text']

            new_plot_text_pairs = []
            for ploti_list, texti_list in plot2text:
                plotl, plotr = ploti_list[0], ploti_list[-1]
                new_plot_text_pairs.append(("".join(new_plot_chunks[plotl:plotr+1]), [new_text_chunks[i] for i in texti_list]))
            
            self.plot_text_pairs = self.plot_text_pairs[:l] + new_plot_text_pairs + self.plot_text_pairs[r:]

    def get_plot(self):
        self.update_plot()
        return self.chapters_writer.get_chapter_content(self.cur_chapter_name)
    
    def get_plot_and_text_containing_text(self, selected_text, context_ratio=0):
        self.update_plot()
        text_chunks = [e[1] for e in self.plot_text_pairs]
        text = self.get_output()
        match = re.search(selected_text, text)  
        if match:  
            start, end = match.span()  
            cumsum = np.cumsum([0, ] + [len(e) for e in chain.from_iterable(text_chunks)]).tolist()
            l, r = bisect.bisect_right(cumsum, start) - 1, bisect.bisect_right(cumsum, end)

            cumsum = np.cumsum([0, ] + [len(e) for e in text_chunks]).tolist()
            plot_l, plot_r = bisect.bisect_right(cumsum, l) - 1, bisect.bisect_right(cumsum, r)
            
            if context_ratio:
                context_length = math.ceil((plot_r - plot_l) * context_ratio)
                plot_l = max(0, plot_l - context_length)
                plot_r = min(len(self.plot_text_pairs), plot_r + context_length)

            return "".join([e[0] for e in self.plot_text_pairs[plot_l:plot_r]]), \
            "".join(chain.from_iterable(e[1] for e in self.plot_text_pairs[plot_l:plot_r]))

            
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

        self.set_output("")

        outputs = yield from run_prompt(
            source="./prompts/生成创作正文的意见",
            chat_messages=[],
            model=self.get_model(),
            config=self.config,
            instruction=human_feedback,
            text="无",
            selected_text="无",
            context=f"###剧情\n{self.get_plot()}",
            )

        outputs = yield from run_prompt(
            source="./prompts/创作正文",
            chat_messages=[],
            model=self.get_model(),
            config=self.config,
            text="无",
            suggestion=outputs['suggestion'],
            context=f"###剧情\n{self.get_plot()}",
            )
        
        newtext = outputs['text']
        
        self.set_output(newtext)

    
    def rewrite_text(self, human_feedback='', selected_text=''):
        assert human_feedback, "意见不能为空！"

        selected_text = selected_text.strip()
        if selected_text:
            assert selected_text in self.get_output(), '选定的用于重写的文本不存在'
        
        assert len(selected_text) > 0, '需要先选定要重写的内容'
        assert len(selected_text) > 7, '需要重写的内容过短'
    
        yield []

        selected_plot_chunk, selected_text_chunk = self.get_plot_and_text_containing_text(selected_text)
        context_plot_chunk, context_text_chunk = self.get_plot_and_text_containing_text(selected_text, context_ratio=1)

        outputs = yield from run_prompt(
            source="./prompts/生成创作正文的意见",
            chat_messages=[],
            model=self.get_model(),
            config=self.config,
            instruction=human_feedback,
            text=context_text_chunk,
            selected_text=selected_text_chunk,
            context=f"###剧情：\n{context_plot_chunk}",
            )

        outputs = yield from run_prompt(
            source="./prompts/创作正文",
            chat_messages=[],
            model=self.get_model(),
            config=self.config,
            text=selected_text_chunk,
            suggestion=outputs['suggestion'],
            context=f"###剧情：\n{selected_plot_chunk}",
            )
        
        newtext = outputs['text']
        
        self.set_output(self.get_output().replace(selected_text_chunk, newtext))

    def construct_context(self, query, index):
        outputs = yield from run_prompt(
            source="./prompts/生成创作正文的上下文",
            chat_messages=[],
            model=self.get_sub_model(),
            config=self.config,
            text=query,
            context=index,
            )
        
        return outputs['knowledge']