from core.writer_utils import KeyPointMsg
from core.writer import Writer

from prompts.创作正文.prompt import main as prompt_draft
class DraftWriter(Writer):
    def __init__(self, xy_pairs, xy_pairs_update_flag=None, model=None, sub_model=None, x_chunk_length=500, y_chunk_length=1000):
        super().__init__(xy_pairs, xy_pairs_update_flag, model, sub_model, x_chunk_length=x_chunk_length, y_chunk_length=y_chunk_length)

    def auto_write(self):
        yield KeyPointMsg(title='一键生成正文', subtitle='新建正文')
        yield from self.write("新建正文")
        
        yield KeyPointMsg(title='一键生成正文', subtitle='扩写正文')
        yield from self.write("扩写正文")
        
        yield KeyPointMsg(title='一键生成正文', subtitle='润色正文')
        yield from self.write("润色正文")

    def write(self, user_prompt):
        init = self.y_len == 0

        yield from self.update_map() 

        if init:
            yield from self.batch_apply(
                prompt_main=prompt_draft,
                user_prompt_text=user_prompt,
                x_span=(0, self.x_len),
                chunk_length=self.x_chunk_length // 3,
                context_length=self.x_chunk_length // 2 // 3,
            )
        else:
            yield from self.batch_apply(
                prompt_main=prompt_draft,
                user_prompt_text=user_prompt,
                y_span=(0, self.y_len),
                chunk_length=self.y_chunk_length // 3,
                context_length=self.y_chunk_length // 4 // 3,
            )

        yield from self.update_map()

        yield from self.batch_apply(
            prompt_main=prompt_draft,
            user_prompt_text="格式化正文",
            y_span=(0, self.y_len),
            chunk_length=self.y_chunk_length,
            context_length=self.y_chunk_length // 4,
            offset=0.25,
            model=self.get_model(),     # 为了保证格式化正文的质量，使用主模型，后续Prompt优化后，可以改回sub_model
        )

    def split_into_chapters(self):
        pass

    def get_model(self):
        return self.model

    def get_sub_model(self):
        return self.sub_model
