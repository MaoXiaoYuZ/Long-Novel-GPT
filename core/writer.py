import numpy as np
import bisect
from dataclasses import asdict, dataclass

from config import MAX_THREAD_NUM
from llm_api import ModelConfig
from prompts.对齐剧情和正文 import prompt as match_plot_and_text
from prompts.审阅.prompt import main as prompt_review
from layers.layer_utils import split_text_into_chunks, detect_max_edit_span, run_yield_func
from core.writer_utils import KeyPointMsg



class Chunk(dict):
    def __init__(self, chunk_pairs: tuple[tuple[str, str, str]], source_slice: tuple[int, int], text_slice: tuple[int, int]):
        super().__init__()
        self['chunk_pairs'] = tuple(chunk_pairs)
        
        if isinstance(source_slice, slice):
            source_slice = (source_slice.start, source_slice.stop)
        self['source_slice'] = source_slice

        if isinstance(text_slice, slice):
            text_slice = (text_slice.start, text_slice.stop)
        assert text_slice[1] is None or text_slice[1] < 0, 'text_slice end must be None or negative'
        self['text_slice'] = text_slice

    def edit(self, x_chunk=None, y_chunk=None, text_pairs=None):
        if x_chunk is not None:
            text_pairs = [(x_chunk, self.y_chunk), ]
        elif y_chunk is not None:
            text_pairs = [(self.x_chunk, y_chunk), ]
        else:
            text_pairs = text_pairs

        chunk_pairs = list(self['chunk_pairs'])
        chunk_pairs[self.text_slice] = list(text_pairs)

        return Chunk(chunk_pairs=tuple(chunk_pairs), source_slice=self.source_slice, text_slice=self.text_slice)
    
    @property
    def source_slice(self) -> slice:
        return slice(*self['source_slice'])

    @property
    def chunk_pairs(self) -> tuple[tuple[str, str]]:
        return self['chunk_pairs']
    
    @property
    def text_slice(self) -> slice:
        return slice(*self['text_slice'])
    
    @property
    def text_source_slice(self) -> slice:
        source_start = self.source_slice.start + self.text_slice.start
        source_stop = self.source_slice.stop + (self.text_slice.stop or 0)
        return slice(source_start, source_stop)
    
    @property
    def text_pairs(self) -> tuple[tuple[str, str]]:
        return self.chunk_pairs[self.text_slice]
    
    @property
    def x_chunk(self) -> str:
        return ''.join(pair[0] for pair in self.text_pairs)
    
    @property
    def y_chunk(self) -> str:
        return ''.join(pair[1] for pair in self.text_pairs)
    
    @property
    def x_chunk_context(self) -> str:
        return ''.join(pair[0] for pair in self.chunk_pairs)
    
    @property
    def y_chunk_context(self) -> str:
        return ''.join(pair[1] for pair in self.chunk_pairs)
    
    
class Writer:
    def __init__(self, xy_pairs, model:ModelConfig=None, sub_model:ModelConfig=None, x_chunk_length=1000, y_chunk_length=1000):
        self.xy_pairs = xy_pairs

        self.model = model
        self.sub_model = sub_model

        self.x_chunk_length = x_chunk_length
        self.y_chunk_length = y_chunk_length

        # x_chunk_length是指一次prompt调用时输入的x长度（由batch_map函数控制）, 此参数会影响到映射到y的扩写率（即：LLM的输出窗口长度/x_chunk_length）
        # 同时，x_chunk_length会影响到map的chunk大小，map的pair大小主要由x_chunk_length决定（具体来说，由update_map函数控制，为x_chunk_length//2)
        # y_chunk_length对pair大小的影响较少（因为映射是一对多）

        self.init_map()
    
    @property
    def x(self):    # TODO: 考虑x经常访问的情况
        return ''.join(pair[0] for pair in self.xy_pairs)

    @property
    def y(self):
        return ''.join(pair[1] for pair in self.xy_pairs)
    
    @property
    def x_len(self):
        return sum(len(pair[0]) for pair in self.xy_pairs)

    @property
    def y_len(self):
        return sum(len(pair[1]) for pair in self.xy_pairs)

    def get_model(self):
        return self.model

    def get_sub_model(self):
        return self.sub_model
    
    def align_span(self, x_span=None, y_span=None):
        if x_span is None and y_span is None:
            raise ValueError("Either x_span or y_span must be provided")
        
        if x_span is not None and y_span is not None:
            raise ValueError("Only one of x_span or y_span should be provided")
        
        is_x = x_span is not None
        z_span = x_span if is_x else y_span
        cumsum_z = np.cumsum([0] + [len(pair[0 if is_x else 1]) for pair in self.xy_pairs]).tolist()
        
        l, r = z_span
        start_chunk = bisect.bisect_right(cumsum_z, l) - 1
        end_chunk = bisect.bisect_left(cumsum_z, r)
        
        aligned_l = cumsum_z[start_chunk]
        aligned_r = cumsum_z[end_chunk]
        
        aligned_span = (aligned_l, aligned_r)
        pair_span = (start_chunk, end_chunk)
        
        # Add assertions to verify the correctness of the output
        assert aligned_l <= l < aligned_r, "aligned_span does not properly contain the start of the input span"
        assert aligned_l < r <= aligned_r, "aligned_span does not properly contain the end of the input span"
        assert 0 <= start_chunk < end_chunk <= len(self.xy_pairs), "pair_span is out of bounds"
        assert sum(len(pair[0 if is_x else 1]) for pair in self.xy_pairs[start_chunk:end_chunk]) == aligned_r - aligned_l, "aligned_span and pair_span do not match"

        return aligned_span, pair_span
    
    def get_chunk(self, pair_span=None, x_span=None, y_span=None, context_length=0, smooth=True):
        if sum(x is not None for x in [pair_span, x_span, y_span]) != 1:
            raise ValueError("Exactly one of pair_span, x_span, or y_span must be provided")
        
        assert pair_span is None or (pair_span[0] >= 0 and pair_span[1] <= len(self.xy_pairs)), "pair_span is out of bounds"

        is_x = x_span is not None
        is_pair = pair_span is not None

        if is_pair:
            context_pair_span = (
                max(0, pair_span[0] - context_length),
                min(len(self.xy_pairs), pair_span[1] + context_length)
            )
        else:
            assert smooth, "smooth must be True"
            span = x_span if is_x else y_span
            if smooth:
                span, pair_span = self.align_span(x_span=span if is_x else None, y_span=span if not is_x else None)

            context_span = (
                max(0, span[0] - context_length),
                min(self.x_len if is_x else self.y_len, span[1] + context_length)
            )

            context_span, context_pair_span = self.align_span(x_span=context_span if is_x else None, y_span=context_span if not is_x else None)

        chunk_pairs = self.xy_pairs[context_pair_span[0]:context_pair_span[1]]
        source_slice = context_pair_span
        text_slice = (pair_span[0] - context_pair_span[0], pair_span[1] - context_pair_span[1])
        assert text_slice[1] <= 0, "text_slice end must be negative"
        text_slice = (text_slice[0], None if text_slice[1] == 0 else text_slice[1])

        return Chunk(
            chunk_pairs=chunk_pairs,
            source_slice=source_slice,
            text_slice=text_slice
        )
    
    def get_chunk_pair_span(self, chunk: Chunk):
        pair_start, pair_end = 0, len(self.xy_pairs)
        x_chunk, y_chunk = chunk.x_chunk, chunk.y_chunk
        for i, (x, y) in enumerate(self.xy_pairs):
            if x_chunk[:50].startswith(x[:50]) and y_chunk[:50].startswith(y[:50]):
                pair_start = i
                break

        for i in range(pair_start, len(self.xy_pairs)):
            x, y = self.xy_pairs[i]
            if x_chunk[-50:].endswith(x[-50:]) and y_chunk[-50:].endswith(y[-50:]):
                pair_end = i + 1
                break

        # Verify the pair_span
        merged_x_chunk = ''.join(p[0] for p in self.xy_pairs[pair_start:pair_end])
        merged_y_chunk = ''.join(p[1] for p in self.xy_pairs[pair_start:pair_end])
        assert x_chunk == merged_x_chunk and y_chunk == merged_y_chunk, "Chunk mismatch"

        return (pair_start, pair_end)
    
    def apply_chunks(self, chunks: list[Chunk], new_chunks: list[Chunk]):
        for chunk, new_chunk in zip(chunks, new_chunks):
            if not isinstance(chunk, Chunk):
                chunk = Chunk(**chunk)
            if not isinstance(new_chunk, Chunk):
                new_chunk = Chunk(**new_chunk)
            
            pair_span = self.get_chunk_pair_span(chunk)
            self.xy_pairs[pair_span[0]:pair_span[1]] = new_chunk.text_pairs
        
    def get_chunks(self, x_span=None, y_span=None, chunk_length=None, context_length=None, offset=0):
        if (x_span is None and y_span is None) or (x_span is not None and y_span is not None):
            raise ValueError("Exactly one of x_span or y_span must be provided")

        is_x = x_span is not None
        span = x_span if is_x else y_span

        if chunk_length is None:
            chunk_length = self.x_chunk_length if is_x else self.y_chunk_length

        if context_length is None:
            context_length = self.x_chunk_length//2 if is_x else self.y_chunk_length//2
        
        if 0 < offset < 1:
            offset = int(chunk_length * offset)

        # Align the span
        aligned_span, _ = self.align_span(x_span=span if is_x else None, y_span=span if not is_x else None)

        # Generate chunks
        chunks = []
        start = aligned_span[0]
        while start < aligned_span[1]:
            if offset > 0:
                end = start + offset
                offset = 0
            else:
                end = start + int(chunk_length * 0.8) # 八二原则，偷个懒，不求最优划分
            end = min(end, aligned_span[1]) 
            chunk_span = (start, end)
            chunk = self.get_chunk(x_span=chunk_span if is_x else None, 
                                 y_span=chunk_span if not is_x else None, 
                                 context_length=context_length, 
                                 smooth=True)
            
            chunks.append(chunk)
            start = sum(len(e[0 if is_x else 1]) for e in self.xy_pairs[:chunk.text_source_slice.stop])

        return chunks

    # TODO: batch_yield 可以考虑输入生成器，而不是函数及参数 
    def batch_yield(self, generators, chunks, prompt_name=None):
        # TODO: 后续考虑只输出new_chunks, 不必重复输出chunks
        if len(generators) > MAX_THREAD_NUM:
            generators = generators[:MAX_THREAD_NUM]
            
        # Process all pairs with the prompt and yield intermediate results
        results = [None] * len(generators)
        yields = [None] * len(generators)
        finished = [False] * len(generators)
        first_iter_flag = True
        while True:
            for i, gen in enumerate(generators):
                if finished[i]:
                    continue
                try:
                    yield_value = next(gen)
                    yields[i] = (yield_value, chunks[i])    # TODO: yield 带上chunk是为了配合前端
                except StopIteration as e:
                    results[i] = e.value
                    finished[i] = True
            
            if all(finished):
                break

            if first_iter_flag and prompt_name is not None:
                yield (kp_msg := KeyPointMsg(prompt_name=prompt_name))
                first_iter_flag = False

            yield [e for e in yields if e is not None]  # 如果是yield的值，那必定为tuple

        if not first_iter_flag and prompt_name is not None:
            yield kp_msg.set_finished()

        return results

    # 临时函数，用于配合前端，返回一个更改，对self施加该更改可以变为cur
    def diff_to(self, cur):
        pre_pointer = 0, 1
        cur_pointer = 0, 1

        cum_sum_pre = np.cumsum([0] + [len(pair[0]) for pair in self.xy_pairs])
        cum_sum_cur = np.cumsum([0] + [len(pair[0]) for pair in cur.xy_pairs])

        apply_chunks = []

        while pre_pointer[1] <= len(self.xy_pairs) and cur_pointer[1] <= len(cur.xy_pairs):
            if cum_sum_pre[pre_pointer[1]] - cum_sum_pre[pre_pointer[0]] == cum_sum_cur[cur_pointer[1]] - cum_sum_cur[cur_pointer[0]]:
                chunk = self.get_chunk(pair_span=pre_pointer)
                value = "".join(pair[1] for pair in cur.xy_pairs[cur_pointer[0]:cur_pointer[1]])
                if value != chunk.y_chunk:
                    apply_chunks.append((chunk, 'y_chunk', value))

                pre_pointer = pre_pointer[1], pre_pointer[1] + 1
                cur_pointer = cur_pointer[1], cur_pointer[1] + 1
            elif cum_sum_pre[pre_pointer[1]] - cum_sum_pre[pre_pointer[0]] < cum_sum_cur[cur_pointer[1]] - cum_sum_cur[cur_pointer[0]]:
                pre_pointer = pre_pointer[0], pre_pointer[1] + 1
            else:
                cur_pointer = cur_pointer[0], cur_pointer[1] + 1
        
        assert pre_pointer[1] == len(self.xy_pairs) + 1 and cur_pointer[1] == len(cur.xy_pairs) + 1

        return apply_chunks

    # 临时函数，用于配合前端
    def apply_chunk(self, chunk:Chunk, key, value):
        if not isinstance(chunk, Chunk):
            chunk = Chunk(**chunk)
        new_chunk = chunk.edit(**{key: value})
        self.apply_chunks([chunk], [new_chunk])
    
    def write_text(self, chunk:Chunk, prompt_main, user_prompt_text, input_keys=None, model=None):
        chunk2prompt_key = {
            'x_chunk': 'x',
            'y_chunk': 'y',
            'x_chunk_context': 'context_x',
            'y_chunk_context': 'context_y'
        }
        
    
        if input_keys is not None:
            prompt_kwargs = {k: getattr(chunk, k) for k in input_keys}
            assert all(prompt_kwargs.values()), "Missing required context keys"
        else:
            prompt_kwargs = {k: getattr(chunk, k) for k in chunk2prompt_key.keys()}
        
        prompt_kwargs = {chunk2prompt_key.get(k, k): v for k, v in prompt_kwargs.items()}
        
        result = yield from prompt_main(
            model=model or self.get_model(),
            user_prompt=user_prompt_text,
            **prompt_kwargs
        )

        return chunk.edit(y_chunk=result['text'])
    
    # 目前review(审阅)的评分机制暂未实装
    def review_text(self, chunk:Chunk, prompt_name, model=None):
        result = yield from prompt_review(
            model=model or self.get_model(),
            prompt_name=prompt_name,
            y=chunk.y_chunk
        )

        return result['text']
    
    # 在init writer时调用
    def init_map(self):
        if self.x and not self.y:
            x_pairs = split_text_into_chunks(self.x, self.x_chunk_length, min_chunk_n=1, min_chunk_size=5, max_chunk_n=20)
            self.xy_pairs = [(x, '') for x in x_pairs]

    def map_text(self, chunk:Chunk):
        # TODO: map会检查映射的内容是否大致匹配，是否有错误映射到context的情况

        x_pairs = split_text_into_chunks(chunk.x_chunk, self.x_chunk_length, min_chunk_n=1, min_chunk_size=5, max_chunk_n=20)
        assert len(x_pairs) >= len(chunk.text_pairs), "x_pairs must be greater than or equal to text_pairs"
        if len(x_pairs) == len(chunk.text_pairs):
            return chunk, True, ''
        y_pairs = split_text_into_chunks(chunk.y_chunk, self.y_chunk_length, min_chunk_n=len(x_pairs), min_chunk_size=5, max_chunk_n=20)


        try:
            gen = match_plot_and_text.main(
                model=self.get_sub_model(),
                plot_chunks=x_pairs,
                text_chunks=y_pairs
                )
            while True:
                yield next(gen)
        except StopIteration as e:
            output = e.value
        
        x2y = output['plot2text']
        new_xy_pairs = []
        for xi_list, yi_list in x2y:
            xl, xr = xi_list[0], xi_list[-1]
            new_xy_pairs.append(("".join(x_pairs[xl:xr+1]), "".join(y_pairs[i] for i in yi_list)))

        new_chunk = chunk.edit(text_pairs=new_xy_pairs)
        return new_chunk, True, ''
    
    def batch_map_text(self, chunks):
        results = yield from self.batch_yield(
            [self.map_text(e) for e in chunks], chunks, prompt_name='映射文本')
        return results
    
    def batch_write_apply_text(self, chunks, prompt_main, user_prompt_text):
        new_chunks = yield from self.batch_yield(
            [self.write_text(e, prompt_main, user_prompt_text) for e in chunks], 
            chunks, prompt_name=user_prompt_text)
        
        results = yield from self.batch_map_text(new_chunks)
        new_chunks2 = [e[0] for e in results]

        self.apply_chunks(chunks, new_chunks2)

    def batch_review_write_apply_text(self, chunks, write_prompt_main, review_prompt_name):
        reviews = yield from self.batch_yield(
            [self.review_text(e, review_prompt_name) for e in chunks], 
            chunks, prompt_name='审阅文本')
        
        rewrite_instrustion = "\n\n根据审阅意见，重新创作，如果审阅意见表示无需改动，则保持原样输出。"

        new_chunks = yield from self.batch_yield(
            [self.write_text(chunk, write_prompt_main, review + rewrite_instrustion) for chunk, review in zip(chunks, reviews)], 
            chunks, prompt_name='创作文本')
        
        results = yield from self.batch_map_text(new_chunks)
        new_chunks2 = [e[0] for e in results]

        self.apply_chunks(chunks, new_chunks2)
