from core.writer_utils import KeyPointMsg
from core.writer import Writer

from prompts.创作正文.prompt import main as prompt_draft
class DraftWriter(Writer):
    def __init__(self, xy_pairs, model=None, sub_model=None, x_chunk_length=500, y_chunk_length=1000):
        super().__init__(xy_pairs, model, sub_model, x_chunk_length=x_chunk_length, y_chunk_length=y_chunk_length)

    def auto_write(self):
        yield KeyPointMsg(title='一键生成正文', subtitle='新建正文')
        yield from self.write("新建正文")
        
        yield KeyPointMsg(title='一键生成正文', subtitle='扩写正文')
        yield from self.write("扩写正文")
        
        yield KeyPointMsg(title='一键生成正文', subtitle='润色正文')
        yield from self.write("润色正文")

    def write(self, user_prompt, y_span=None):
        init = self.y_len == 0

        if init:
            chunks = self.get_chunks(
                x_span=(0, self.x_len),
            )
        else:
            chunks = self.get_chunks(
                y_span=y_span or (0, self.y_len),
            )
        
        if user_prompt == '自动' and init:
            user_prompt = '新建正文'

        if user_prompt == '自动':
            yield from self.batch_review_write_apply_text(chunks, prompt_draft, "审阅正文")
        else:
            yield from self.batch_write_apply_text(chunks, prompt_draft, user_prompt)

    def split_into_chapters(self):
        pass

    def get_model(self):
        return self.model

    def get_sub_model(self):
        return self.sub_model
