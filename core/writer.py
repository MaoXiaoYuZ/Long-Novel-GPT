import re
import numpy as np
import bisect
from dataclasses import asdict, dataclass

from llm_api import ModelConfig
from prompts.对齐剧情和正文 import prompt as match_plot_and_text
from prompts.审阅.prompt import main as prompt_review
from core.writer_utils import split_text_into_chunks, detect_max_edit_span, run_yield_func
from core.writer_utils import KeyPointMsg
from core.diff_utils import get_chunk_changes


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
    def x_chunk_len(self) -> int:
        return sum(len(pair[0]) for pair in self.text_pairs)
    
    @property
    def y_chunk_len(self) -> int:
        return sum(len(pair[1]) for pair in self.text_pairs)
    
    @property
    def x_chunk_context(self) -> str:
        return ''.join(pair[0] for pair in self.chunk_pairs)
    
    @property
    def y_chunk_context(self) -> str:
        return ''.join(pair[1] for pair in self.chunk_pairs)
    
    @property
    def x_chunk_context_len(self) -> int:
        return sum(len(pair[0]) for pair in self.chunk_pairs)
    
    @property
    def y_chunk_context_len(self) -> int:
        return sum(len(pair[1]) for pair in self.chunk_pairs)
    
    
class Writer:
    def __init__(self, xy_pairs, global_context=None, model:ModelConfig=None, sub_model:ModelConfig=None, x_chunk_length=1000, y_chunk_length=1000, max_thread_num=5):
        self.xy_pairs = xy_pairs
        self.global_context = global_context or {}

        self.model = model
        self.sub_model = sub_model

        self.x_chunk_length = x_chunk_length
        self.y_chunk_length = y_chunk_length

        # x_chunk_length是指一次prompt调用时输入的x长度（由batch_map函数控制）, 此参数会影响到映射到y的扩写率（即：LLM的输出窗口长度/x_chunk_length）
        # 同时，x_chunk_length会影响到map的chunk大小，map的pair大小主要由x_chunk_length决定（具体来说，由update_map函数控制，为x_chunk_length//2)
        # y_chunk_length对pair大小的影响较少（因为映射是一对多）

        self.max_thread_num = max_thread_num    # 使得可以单独控制某个chunk变量的线程数，这在同时运行多个Writer变量时有用
    
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
    
    def count_span_length(self, span):
        pairs = self.xy_pairs[span[0]:span[1]]
        return sum(len(pair[0]) for pair in pairs), sum(len(pair[1]) for pair in pairs)

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
        pair_start, pair_end = chunk.text_source_slice.start, chunk.text_source_slice.stop
        merged_x_chunk = ''.join(p[0] for p in self.xy_pairs[pair_start:pair_end])
        merged_y_chunk = ''.join(p[1] for p in self.xy_pairs[pair_start:pair_end])
        if merged_x_chunk == chunk.x_chunk and merged_y_chunk == chunk.y_chunk:
            return pair_start, pair_end

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
        occupied_pair_span = [False] * len(self.xy_pairs)
        pair_span_list = [self.get_chunk_pair_span(e) for e in chunks]
        for pair_span in pair_span_list:
            assert not any(occupied_pair_span[pair_span[0]:pair_span[1]]), "Chunk overlap"
            occupied_pair_span[pair_span[0]:pair_span[1]] = [True] * (pair_span[1] - pair_span[0])
        # TODO: 这里可以验证occupied_pair_span是否全被占据
        new_pairs_list = [e.text_pairs for e in new_chunks]

        sorted_spans_with_new_pairs = sorted(
            zip(pair_span_list, new_pairs_list),
            key=lambda x: x[0][0],
            reverse=True
        )

        for (start, end), new_pairs in sorted_spans_with_new_pairs:
            self.xy_pairs[start:end] = new_pairs

    def get_chunks(self, pair_span=None, chunk_length_ratio=1, context_length_ratio=1, offset_ratio=0):
        pair_span = pair_span or (0, len(self.xy_pairs))
        chunk_length = self.x_chunk_length * chunk_length_ratio, self.y_chunk_length * chunk_length_ratio
        context_length = self.x_chunk_length//2 * context_length_ratio, self.y_chunk_length//2 * context_length_ratio
        
        if 0 < offset_ratio < 1:
            offset_ratio = int(chunk_length[0] * offset_ratio), int(chunk_length[1] * offset_ratio)

        # Generate chunks
        chunks = []
        start = pair_span[0]
        cstart = self.count_span_length((0, start))  # char_start
        max_cend = self.count_span_length((0, pair_span[1]))  # char_end
        while start < pair_span[1]:
            if offset_ratio != 0:
                cend = cstart[0] + offset_ratio[0], cstart[1] + offset_ratio[1]
                offset_ratio = 0
            else:
                cend = cstart[0] + int(chunk_length[0] * 0.8), cstart[1] + int(chunk_length[1] * 0.8) # 八二原则，偷个懒，不求最优划分
            cend = min(cend[0], max_cend[0]), min(cend[1], max_cend[1])

            # 选择非零长度的span来获取chunk
            x_len, y_len = cend[0] - cstart[0], cend[1] - cstart[1]
            if x_len > 0:
                chunk1 = self.get_chunk(x_span=(cstart[0], cend[0]), context_length=context_length[0])
            if y_len > 0:
                chunk2 = self.get_chunk(y_span=(cstart[1], cend[1]), context_length=context_length[1])
            
            if x_len > 0 and y_len == 0:
                chunk = chunk1
            elif x_len == 0 and y_len > 0:
                chunk = chunk2
            elif x_len > 0 and y_len > 0:
                # 选其中source_slice更小的chunk
                chunk = chunk1 if chunk1.source_slice.stop - chunk1.source_slice.start < chunk2.source_slice.stop - chunk2.source_slice.start else chunk2
            else:
                raise ValueError("Both x_span and y_span have zero length")
             
            # assert chunk.x_chunk_context_len <= self.x_chunk_length * 2 and chunk.y_chunk_context_len <= self.y_chunk_length * 2, \
            #     "无法获取到一个足够短的区块，请调整区块长度或窗口长度！"

            chunks.append(chunk)
            start = chunk.text_source_slice.stop
            cstart = self.count_span_length((0, start))

        return chunks

    # TODO: batch_yield 可以考虑输入生成器，而不是函数及参数 
    def batch_yield(self, generators, chunks, prompt_name=None):
        # TODO: 后续考虑只输出new_chunks, 不必重复输出chunks

        # Process all pairs with the prompt and yield intermediate results
        results = [None] * len(generators)
        yields = [None] * len(generators)
        finished = [False] * len(generators)
        first_iter_flag = True
        while True:
            co_num = 0
            for i, gen in enumerate(generators):
                if finished[i]:
                    continue

                try:
                    co_num += 1
                    yield_value = next(gen)
                    yields[i] = (yield_value, chunks[i])    # TODO: yield 带上chunk是为了配合前端
                except StopIteration as e:
                    results[i] = e.value
                    finished[i] = True
                    if yields[i] is None: yields[i] = (None, chunks[i])
                
                if co_num >= self.max_thread_num:
                        break
            
            if all(finished):
                break

            if first_iter_flag and prompt_name is not None:
                yield (kp_msg := KeyPointMsg(prompt_name=prompt_name))
                first_iter_flag = False

            yield yields  # 如果是yield的值，那必定为tuple

        if not first_iter_flag and prompt_name is not None:
            yield kp_msg.set_finished()

        return results

    # 临时函数，用于配合前端，返回一个更改，对self施加该更改可以变为cur
    def diff_to(self, cur, pair_span=None):
        if pair_span is None:
            pair_span = (0, len(self.xy_pairs))
        
        if self.count_span_length(pair_span)[0] == 0:
            # 2.1版本中，章节和剧情的创作不参考x
            pair_span2 = (0 + pair_span[0], len(cur.xy_pairs) - (len(self.xy_pairs) - pair_span[1]))
            y_list = [e[1] for e in self.xy_pairs[pair_span[0]:pair_span[1]]] 
            y2_list =[e[1] for e in cur.xy_pairs[pair_span2[0]:pair_span2[1]]]
            
            y_list += ['',] * max(len(y2_list) - len(y_list), 0)
            y2_list += ['',] * max(len(y_list) - len(y2_list), 0)

            data_chunks = [('', y, y2) for y, y2 in zip(y_list, y2_list)]

            return data_chunks

        pre_pointer = 0, 1
        cur_pointer = 0, 1

        cum_sum_pre = np.cumsum([0] + [len(pair[0]) for pair in self.xy_pairs])
        cum_sum_cur = np.cumsum([0] + [len(pair[0]) for pair in cur.xy_pairs])

        apply_chunks = []

        while pre_pointer[1] <= len(self.xy_pairs) and cur_pointer[1] <= len(cur.xy_pairs):
            if cum_sum_pre[pre_pointer[1]] - cum_sum_pre[pre_pointer[0]] == cum_sum_cur[cur_pointer[1]] - cum_sum_cur[cur_pointer[0]]:
                chunk = self.get_chunk(pair_span=pre_pointer)
                value = "".join(pair[1] for pair in cur.xy_pairs[cur_pointer[0]:cur_pointer[1]])
                apply_chunks.append((chunk, 'y_chunk', value))

                pre_pointer = pre_pointer[1], pre_pointer[1] + 1
                cur_pointer = cur_pointer[1], cur_pointer[1] + 1
            elif cum_sum_pre[pre_pointer[1]] - cum_sum_pre[pre_pointer[0]] < cum_sum_cur[cur_pointer[1]] - cum_sum_cur[cur_pointer[0]]:
                pre_pointer = pre_pointer[0], pre_pointer[1] + 1
            else:
                cur_pointer = cur_pointer[0], cur_pointer[1] + 1
        
        assert pre_pointer[1] == len(self.xy_pairs) + 1 and cur_pointer[1] == len(cur.xy_pairs) + 1

        filtered_apply_chunks = []
        for e in apply_chunks:
            text_source_slice = e[0].text_source_slice
            if text_source_slice.start >= pair_span[0] and text_source_slice.stop <= pair_span[1]:
                filtered_apply_chunks.append(e)

        data_chunks = []
        for chunk, key, value in filtered_apply_chunks:
            data_chunks.append((chunk.x_chunk, chunk.y_chunk, value))

        return data_chunks

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

        prompt_kwargs.update(self.global_context)   # prompt_kwargs会把所有的信息都带上，至于要用哪些由prompt决定
        
        result = yield from prompt_main(
            model=model or self.get_model(),
            user_prompt=user_prompt_text,
            **prompt_kwargs
        )

        # 为了在V2.2版本兼容summary_prompt, 后续text_key这种设计会舍弃
        update_dict = {}
        if 'text_key' in result:
            update_dict[result['text_key']] = result['text']
        else:
            update_dict['y_chunk'] = result['text']

        return chunk.edit(**update_dict)
    
    # 目前review(审阅)的评分机制暂未实装
    def review_text(self, chunk:Chunk, prompt_name, model=None):
        result = yield from prompt_review(
            model=model or self.get_model(),
            prompt_name=prompt_name,
            y=chunk.y_chunk
        )

        return result['text']

    def map_text_wo_llm(self, chunk:Chunk):
        # 该函数尝试不用LLM进行映射，目标是保证chunk.pairs中每个pair的长度合适，如果长了，进行划分，如果无法划分，报错
        new_xy_pairs = []
        for x, y in chunk.text_pairs:
            if x.strip() and not y.strip():
                x_pairs = split_text_into_chunks(x, self.x_chunk_length, min_chunk_n=1, min_chunk_size=5)
                new_xy_pairs.extend([(x_pair, y) for x_pair in x_pairs])
            elif not x.strip() and y.strip():
                y_pairs = split_text_into_chunks(y, self.y_chunk_length, min_chunk_n=1, min_chunk_size=5)
                new_xy_pairs.extend([(x, y_pair) for y_pair in y_pairs])
            else:
                if len(x) > self.x_chunk_length or len(y) > self.y_chunk_length:
                    raise ValueError("窗口太小或段落太长!考虑选择更大的窗口长度或手动分段。")
                new_xy_pairs.append((x, y))
        
        return chunk.edit(text_pairs=new_xy_pairs)

    def map_text(self, chunk:Chunk):
        # TODO: map会检查映射的内容是否大致匹配，是否有错误映射到context的情况

        if chunk.x_chunk.strip():
            x_pairs = split_text_into_chunks(chunk.x_chunk, self.x_chunk_length, min_chunk_n=1, min_chunk_size=5, max_chunk_n=20)
            assert len(x_pairs) >= len(chunk.text_pairs), "未知错误！合并所有区块后再分区块，结果更少？"
            if len(x_pairs) == len(chunk.text_pairs):
                return chunk, True, ''
        else:
            # 这说明y的创作是不参照x的，而是参照global_context
            y_pairs = split_text_into_chunks(chunk.y_chunk, self.y_chunk_length, min_chunk_n=1, min_chunk_size=5, max_chunk_n=20)
            new_xy_pairs = [('', y) for y in y_pairs]
            return chunk.edit(text_pairs=new_xy_pairs), True, ''

        try:
            y_pairs = split_text_into_chunks(chunk.y_chunk, self.y_chunk_length, min_chunk_n=len(x_pairs), min_chunk_size=5, max_chunk_n=20)
        except Exception as e:
            # 如果y_chunk不能找到更多的区块划分，干脆让x_chunk划分更少的区块
            y_pairs = split_text_into_chunks(chunk.y_chunk, self.y_chunk_length, min_chunk_n=1, min_chunk_size=5, max_chunk_n=20)
            x_pairs = split_text_into_chunks(chunk.x_chunk, self.x_chunk_length, min_chunk_n=1, min_chunk_size=5, max_chunk_n=int(0.8 * len(y_pairs)))
            
            # TODO: 这是因为目前映射Prompt的设计需要x数量小于y，后续会对Prompt进行改进

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
            chunks, prompt_name='创作文本')
        
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
