from core.writer_utils import KeyPointMsg
from core.writer import Writer

from prompts.创作正文.prompt import main as prompt_draft
from prompts.提炼.prompt import main as prompt_summary


class DraftWriter(Writer):
    def __init__(self, xy_pairs, global_context, model=None, sub_model=None, x_chunk_length=500, y_chunk_length=1000, max_thread_num=5):
        super().__init__(xy_pairs, global_context, model, sub_model, x_chunk_length=x_chunk_length, y_chunk_length=y_chunk_length, max_thread_num=max_thread_num)

    def write(self, user_prompt, pair_span=None):
        target_chunk = self.get_chunk(pair_span=pair_span)
        if not target_chunk.x_chunk:
            raise Exception("需要提供剧情。")
        if len(target_chunk.x_chunk) <= 5:
            raise Exception("剧情不能少于5个字。")

        chunks = self.get_chunks(pair_span)
        
        yield from self.batch_write_apply_text(chunks, prompt_draft, user_prompt)

    def summary(self, pair_span=None):
        target_chunk = self.get_chunk(pair_span=pair_span)
        if not target_chunk.y_chunk:
            raise Exception("没有正文需要总结。")
        if len(target_chunk.y_chunk) <= 5:
            raise Exception("需要总结的正文不能少于5个字。")
        
        # 先分割为更小的块，这样get_chunks才能正常工作
        new_target_chunk = self.map_text_wo_llm(target_chunk)
        self.apply_chunks([target_chunk], [new_target_chunk])
        chunk_span = self.get_chunk_pair_span(new_target_chunk)

        chunks = self.get_chunks(chunk_span, context_length_ratio=0)

        yield from self.batch_write_apply_text(chunks, prompt_summary, "提炼剧情")

    def split_into_chapters(self):
        pass

    def get_model(self):
        return self.model

    def get_sub_model(self):
        return self.sub_model
