from core.writer_utils import KeyPointMsg
from core.writer import Writer

from prompts.创作剧情.prompt import main as prompt_plot

class PlotWriter(Writer):
    def __init__(self, xy_pairs, xy_pairs_update_flag=None, model=None, sub_model=None, x_chunk_length=200, y_chunk_length=1000):
        super().__init__(xy_pairs, xy_pairs_update_flag, model, sub_model, x_chunk_length=x_chunk_length, y_chunk_length=y_chunk_length)

    def auto_write(self):
        yield KeyPointMsg(title='一键生成剧情', subtitle='新建剧情')
        yield from self.write("新建剧情")
        
        yield KeyPointMsg(title='一键生成剧情', subtitle='扩写剧情')
        yield from self.write("扩写剧情")
        
        yield KeyPointMsg(title='一键生成剧情', subtitle='润色剧情')
        yield from self.write("润色剧情")

    def write(self, user_prompt):
        init = self.y_len == 0

        yield from self.update_map() 

        if init:
            yield from self.batch_apply(
                prompt_main=prompt_plot,
                user_prompt_text=user_prompt,
                x_span=(0, self.x_len),
                chunk_length=self.x_chunk_length // 3,
                context_length=self.x_chunk_length // 2 // 3,
            )
        else:
            yield from self.batch_apply(
                prompt_main=prompt_plot,
                user_prompt_text=user_prompt,
                y_span=(0, self.y_len),
                chunk_length=self.y_chunk_length // 3,
                context_length=self.y_chunk_length // 4 // 3,
            )

        yield from self.update_map()

        yield from self.batch_apply(
            prompt_main=prompt_plot,
            user_prompt_text="格式化剧情",
            y_span=(0, self.y_len),
            chunk_length=self.y_chunk_length,
            context_length=self.y_chunk_length // 4,
            offset=0.25,
            model=self.get_sub_model(),
        )

    def split_into_chapters(self):
        pass

    def get_model(self):
        return self.model

    def get_sub_model(self):
        return self.sub_model
