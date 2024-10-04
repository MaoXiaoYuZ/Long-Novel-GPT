from collections import defaultdict
import math
import re

from layers.writer import ChatMessages
from layers.layer_utils import split_text_into_paragraphs, detect_max_edit_span, run_yield_func

import numpy as np
from itertools import chain 
import bisect

from llm_api import ModelConfig
from prompts.对齐剧情和正文 import prompt as match_plot_and_text
from prompts.生成重写正文的意见 import prompt as generate_rewrite_suggestion
from prompts.根据提纲创作正文 import prompt as init_text
from prompts.根据意见重写正文 import prompt as generate_rewrite_text

class NovelWriter():
    def __init__(self, plot, text, plot_text_pairs=None, model:ModelConfig=None, sub_model:ModelConfig=None):
        self.plot = plot
        self.text = text
        self.plot_text_pairs = plot_text_pairs or []
        self.model = model
        self.sub_model = sub_model

    # update_plot(plot和text之间映射关系的建立)是独立于update_text的。
    # 也就是说，update_plot不依赖于记录每次text的更改，自己会维护一个记录。
    # 这样避免了update_text时引入更多的操作，造成更多开销。
    # 也便于实现lazy_update, 在查询某段text对应的plot时才更新plot和text映射。
    def update_plot(self):
        plot = self.plot
        text = self.get_output()

        if not text.strip():
            return

        if self.plot_text_pairs and all(len(e) == 2 for e in self.plot_text_pairs):
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
                plot_l, plot_r = bisect.bisect_right(cumsum, l) - 1, min(bisect.bisect_right(cumsum, cumsum[-1] + r), len(plot_chunks))
                text_l, text_r = cumsum[plot_l], cumsum[plot_r]

                self._update_plot(plot_l, plot_r, new_text_chunks=new_text_chunks[text_l: len(new_text_chunks) - (cumsum[-1] - text_r)])
        else:
            plot_chunks, text_chunks = split_text_into_paragraphs(plot), split_text_into_paragraphs(text)
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
            try:
                gen = match_plot_and_text.main(
                    model=self.get_sub_model(),
                    plot_chunks=new_plot_chunks,
                    text_chunks=new_text_chunks
                    )
                while True:
                    next(gen)
            except StopIteration as e:
                output = e.value
            
            plot2text = output['plot2text']

            new_plot_text_pairs = []
            for ploti_list, texti_list in plot2text:
                plotl, plotr = ploti_list[0], ploti_list[-1]
                new_plot_text_pairs.append(("".join(new_plot_chunks[plotl:plotr+1]), [new_text_chunks[i] for i in texti_list]))
            
            self.plot_text_pairs = self.plot_text_pairs[:l] + new_plot_text_pairs + self.plot_text_pairs[r:]

    def get_plot(self):
        return self.plot
    
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
        return self.text
    
    def set_output(self, chapter_text):
        self.text = chapter_text
        self.update_plot()

    def init_text(self):
        outputs = yield from init_text.main(
            model=self.get_model(),
            chapter=self.get_plot(),
        )

        newtext = outputs['text']
        return newtext

    def generate_rewrite_suggestion(self, selected_span):
        selected_text = self.get_output()[selected_span[0]:selected_span[1]]

        context_plot_chunk, context_text_chunk = self.get_plot_and_text_containing_text(selected_text, context_ratio=1)

        outputs = yield from generate_rewrite_suggestion.main(
            model=self.get_model(),
            chapter=context_plot_chunk,
            text=context_text_chunk,
            selected_text=selected_text,
        )

        return outputs['suggestion']

    def generate_rewrite_text(self, suggestion, selected_span):
        selected_text = self.get_output()[selected_span[0]:selected_span[1]]

        selected_plot_chunk, selected_text_chunk = self.get_plot_and_text_containing_text(selected_text)

        outputs = yield from generate_rewrite_text.main(
            model=self.get_model(),
            chapter=selected_plot_chunk,
            text=selected_text_chunk,
            selected_text=selected_text,
            suggestion=suggestion,
        )

        return outputs['text']

    def get_model(self):
        return self.model

    def get_sub_model(self):
        return self.sub_model
