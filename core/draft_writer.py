from collections import defaultdict
import math
import re

from layers.writer import ChatMessages
from layers.layer_utils import split_text_into_chunks, detect_max_edit_span, run_yield_func

import numpy as np
from itertools import chain 
import bisect

from llm_api import ModelConfig
from prompts.生成重写正文的意见 import prompt as generate_rewrite_suggestion
from prompts.根据提纲创作正文 import prompt as init_text
from prompts.根据意见重写正文 import prompt as generate_rewrite_text

from core.writer import Writer

class DraftWriter(Writer):
    def __init__(self, xy_pairs, xy_pairs_update_flag=None, model=None, sub_model=None, x_chunk_length=500, y_chunk_length=2000):
        super().__init__(xy_pairs, xy_pairs_update_flag, model, sub_model, x_chunk_length=x_chunk_length, y_chunk_length=y_chunk_length)

    def init_text(self, suggestion, x_span=None):
        self.xy_pairs = [(e[0], '') for e in self.xy_pairs]

        yield from self.update_map()

        def process_chunk(chunk):
            return init_text.main(
                model=self.get_model(),
                context_x=chunk.x_chunk_context,
                x=chunk.x_chunk,
                suggestion=suggestion
            )
        
        if x_span is None:
            x_span = (0, self.x_len)

        results = yield from self.batch_map(
            prompt=process_chunk,
            x_span=x_span,
            smooth=True
        )

        return results
    
    def rewrite_text(self, suggestion, x_span=None, offset=0.25):
        yield from self.update_map()

        def process_chunk(chunk):
            return generate_rewrite_text.main(
                model=self.get_model(),
                context_x=chunk.x_chunk_context,
                context_y=chunk.y_chunk_context,
                y=chunk.y_chunk,
                suggestion=suggestion
            )
        
        if x_span is None:
            x_span = (0, self.x_len)

        results = yield from self.batch_map(
            prompt=process_chunk,
            x_span=x_span,
            smooth=True,
            offset=offset
        )

        return results

    def generate_rewrite_suggestion(self, selected_span):
        selected_text = self.y[selected_span[0]:selected_span[1]]

        yield from self.update_map()

        context_plot_chunk, context_text_chunk = self.get_plot_and_text_containing_text(selected_text, context_ratio=1)

        outputs = yield from generate_rewrite_suggestion.main(
            model=self.get_model(),
            chapter=context_plot_chunk,
            text=context_text_chunk,
            selected_text=selected_text,
        )

        return outputs['suggestion']

    def generate_rewrite_text(self, suggestion, selected_span):
        selected_text = self.y[selected_span[0]:selected_span[1]]

        yield from self.update_map()

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
