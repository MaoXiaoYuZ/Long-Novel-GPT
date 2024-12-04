from core.writer_utils import KeyPointMsg
from core.writer import Writer

from prompts.创作大纲.prompt import main as prompt_outline

class OutlineWriter(Writer):
    def __init__(self, xy_pairs, model=None, sub_model=None, x_chunk_length=10_000, y_chunk_length=10_000):
        super().__init__(xy_pairs, model, sub_model, x_chunk_length=x_chunk_length, y_chunk_length=y_chunk_length)

    def auto_write(self):
        yield KeyPointMsg(title='一键生成大纲', subtitle='新建大纲')
        yield from self.write("新建大纲", x_span=(0, self.x_len))
        
        yield KeyPointMsg(title='一键生成大纲', subtitle='扩写大纲')
        yield from self.write("扩写大纲", x_span=(0, self.x_len))
        
        yield KeyPointMsg(title='一键生成大纲', subtitle='润色大纲')
        yield from self.write("润色大纲", x_span=(0, self.x_len))

    def write(self, user_prompt, pair_span=None):
        chunks = chunks = self.get_chunks(pair_span)

        yield from self.batch_write_apply_text(chunks, prompt_outline, user_prompt)


    def get_model(self):
        return self.model

    def get_sub_model(self):
        return self.sub_model
