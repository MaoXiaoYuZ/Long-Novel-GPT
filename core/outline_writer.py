from core.parser_utils import parse_chapters
from core.writer_utils import KeyPointMsg
from core.writer import Writer

from prompts.创作章节.prompt import main as prompt_outline
from prompts.提炼.prompt import main as prompt_summary

class OutlineWriter(Writer):
    def __init__(self, xy_pairs, global_context, model=None, sub_model=None, x_chunk_length=2_000, y_chunk_length=2_000, max_thread_num=5):
        super().__init__(xy_pairs, global_context, model, sub_model, x_chunk_length=x_chunk_length, y_chunk_length=y_chunk_length, max_thread_num=max_thread_num)

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
            chunks, prompt_name='创作文本')
        
        results = yield from self.batch_split_chapters(new_chunks)

        new_chunks2 = [e[0] for e in results]

        self.apply_chunks(chunks, new_chunks2)

    def split_chapters(self, chunk):
        if False: yield # 将此函数变为生成器函数

        assert chunk.x_chunk == '', 'chunk.x_chunk不为空'
        chapter_titles, chapter_contents = parse_chapters(chunk.y_chunk)
        new_xy_pairs = self.construct_xy_pairs(chapter_titles, chapter_contents)
        
        return chunk.edit(text_pairs=new_xy_pairs), True, ''
    
    def construct_xy_pairs(self, chapter_titles, chapter_contents):
        return [('', f"{title[0]} {title[1]}\n{content}") for title, content in zip(chapter_titles, chapter_contents)]
    
    def batch_split_chapters(self, chunks):
        results = yield from self.batch_yield(
            [self.split_chapters(e) for e in chunks], chunks, prompt_name='划分章节')
        return results
    
    def summary(self):
        target_chunk = self.get_chunk(pair_span=(0, len(self.xy_pairs)))
        if not target_chunk.y_chunk:
            raise Exception("没有章节需要总结。")
        if len(target_chunk.y_chunk) <= 5:
            raise Exception("需要总结的章节不能少于5个字。")
        
        if len(target_chunk.y_chunk) > 2000:
            y = self._truncate_chunk(target_chunk.y_chunk)
        else:
            y = target_chunk.y_chunk
    
        result = yield from prompt_summary(self.model, "提炼大纲", y=y)

        self.global_context['outline'] = result['text']

    def get_model(self):
        return self.model

    def get_sub_model(self):
        return self.sub_model

    def _truncate_chunk(self, text, chunk_size=100, keep_chunks=20):
        """Truncate chunk content by keeping evenly spaced sections"""
        if len(text) <= 2000:
            return text
        
        # Split into chunks of chunk_size
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        
        # Select evenly spaced chunks
        step = len(chunks) // keep_chunks
        selected_chunks = chunks[::step][:keep_chunks]
        new_content = '...'.join(selected_chunks)
        return new_content
        