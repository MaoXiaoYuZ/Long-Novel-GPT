from core.writer_utils import KeyPointMsg
from core.writer import Writer

from prompts.创作剧情.prompt import main as prompt_plot

class PlotWriter(Writer):
    def __init__(self, xy_pairs, global_context, model=None, sub_model=None, x_chunk_length=200, y_chunk_length=1000):
        super().__init__(xy_pairs, global_context, model, sub_model, x_chunk_length=x_chunk_length, y_chunk_length=y_chunk_length)

    def write(self, user_prompt, pair_span=None):
        target_chunk = self.get_chunk(pair_span=pair_span)

        if not self.global_context.get("chapter", ''):
            raise Exception("需要提供章节内容。")
        
        if not target_chunk.y_chunk.strip():
            if not self.y.strip():
                chunks = [target_chunk, ]
            else:
                raise Exception("选中进行创作的内容不能为空，考虑随便填写一些占位的字。")
        else:
            chunks = self.get_chunks(pair_span)

        new_chunks = yield from self.batch_yield(
            [self.write_text(e, prompt_plot, user_prompt) for e in chunks], 
            chunks, prompt_name=user_prompt)
        
        results = yield from self.batch_map_text(new_chunks)
        new_chunks2 = [e[0] for e in results]

        self.apply_chunks(chunks, new_chunks2)

    def get_model(self):
        return self.model

    def get_sub_model(self):
        return self.sub_model
