from core.writer_utils import KeyPointMsg
from core.writer import Writer

from prompts.创作大纲.prompt import main as prompt_outline

class OutlineWriter(Writer):
    def __init__(self, xy_pairs, xy_pairs_update_flag=None, model=None, sub_model=None, x_chunk_length=10_000, y_chunk_length=10_000):
        super().__init__(xy_pairs, xy_pairs_update_flag, model, sub_model, x_chunk_length=x_chunk_length, y_chunk_length=y_chunk_length)

    def auto_write(self):
        yield KeyPointMsg(title='一键生成大纲', subtitle='新建大纲')
        yield from self.write("新建大纲", x_span=(0, self.x_len))
        
        yield KeyPointMsg(title='一键生成大纲', subtitle='扩写大纲')
        yield from self.write("扩写大纲", x_span=(0, self.x_len))
        
        yield KeyPointMsg(title='一键生成大纲', subtitle='润色大纲')
        yield from self.write("润色大纲", x_span=(0, self.x_len))

    def write(self, user_prompt, x_span=None):
        init = self.y_len == 0

        yield from self.update_map() 

        yield from self.batch_apply(
            prompt_main=prompt_outline,
            user_prompt_text=user_prompt,
            x_span=x_span or (0, self.x_len),
            chunk_length=self.x_chunk_length // 3,
            context_length=self.x_chunk_length // 2 // 3,
        )

        yield from self.update_map()

        yield from self.batch_apply(
            prompt_main=prompt_outline,
            user_prompt_text="格式化大纲",
            x_span=x_span or (0, self.x_len),
            chunk_length=self.x_chunk_length,
            context_length=self.x_chunk_length // 2,
            offset=0.25,
            model=self.get_sub_model(),
        )

    def get_model(self):
        return self.model

    def get_sub_model(self):
        return self.sub_model
