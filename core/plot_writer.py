from core.writer import Writer

from prompts.创作剧情初稿 import prompt as init_plot
from prompts.根据意见重写剧情 import prompt as rewrite_plot


class PlotWriter(Writer):
    def __init__(self, xy_pairs, xy_pairs_update_flag=None, model=None, sub_model=None, x_chunk_length=100, y_chunk_length=1000):
        super().__init__(xy_pairs, xy_pairs_update_flag, model, sub_model, x_chunk_length=x_chunk_length, y_chunk_length=y_chunk_length)

    def init_text(self, suggestion, x_span=None):
        self.xy_pairs = [(e[0], '') for e in self.xy_pairs]

        yield from self.update_map()

        def process_chunk(chunk):
            return init_plot.main(
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
            return rewrite_plot.main(
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
    
    def split_into_chapters(self):
        pass

    def get_model(self):
        return self.model

    def get_sub_model(self):
        return self.sub_model
