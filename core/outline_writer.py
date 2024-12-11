from core.parser_utils import parse_chapters
from core.writer_utils import KeyPointMsg
from core.writer import Writer

from prompts.创作章节.prompt import main as prompt_outline

class OutlineWriter(Writer):
    def __init__(self, xy_pairs, global_context, model=None, sub_model=None, x_chunk_length=2_000, y_chunk_length=2_000):
        super().__init__(xy_pairs, global_context, model, sub_model, x_chunk_length=x_chunk_length, y_chunk_length=y_chunk_length)

    def write(self, user_prompt, pair_span=None):
        target_chunk = self.get_chunk(pair_span=pair_span)

        if not self.global_context.get("summary", ''):
            raise Exception("需要提供小说简介。")
        
        if not target_chunk.y_chunk.strip():
            if not self.y.strip():
                chunks = [target_chunk, ]
            else:
                raise Exception("选中进行创作的内容不能为空，考虑随便填写一些占位的字。")
        else:
            chunks = self.get_chunks(pair_span)

        new_chunks = yield from self.batch_yield(
            [self.write_text(e, prompt_outline, user_prompt) for e in chunks], 
            chunks, prompt_name=user_prompt)
        
        results = yield from self.batch_split_chapters(new_chunks)

        new_chunks2 = [e[0] for e in results]

        self.apply_chunks(chunks, new_chunks2)

    def split_chapters(self, chunk):
        if False: yield # 将此函数变为生成器函数

        assert chunk.x_chunk == '', 'chunk.x_chunk不为空'
        chapter_titles, chapter_contents = parse_chapters(chunk.y_chunk)
        new_xy_pairs = [('', f"{title[0]} {title[1]}\n{content}") for title, content in zip(chapter_titles, chapter_contents)]
        
        return chunk.edit(text_pairs=new_xy_pairs), True, ''
    
    def batch_split_chapters(self, chunks):
        results = yield from self.batch_yield(
            [self.split_chapters(e) for e in chunks], chunks, prompt_name='划分章节')
        return results

    def get_model(self):
        return self.model

    def get_sub_model(self):
        return self.sub_model
