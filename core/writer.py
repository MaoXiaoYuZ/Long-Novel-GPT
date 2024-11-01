import numpy as np
import bisect
from dataclasses import asdict, dataclass

from config import MAX_THREAD_NUM
from llm_api import ModelConfig
from prompts.对齐剧情和正文 import prompt as match_plot_and_text
from layers.layer_utils import split_text_into_chunks, detect_max_edit_span, run_yield_func
from core.writer_utils import KeyPointMsg

@dataclass
class Chunk:
    pair_span: tuple[int, int] | None
    x_span: tuple[int, int] | None
    y_span: tuple[int, int] | None
    x_segment: str | None
    y_segment: str | None
    x_chunk: str
    y_chunk: str
    x_chunk_context: str
    y_chunk_context: str
    x_relative_span: tuple[int, int] | None
    y_relative_span: tuple[int, int] | None


class Writer:
    def __init__(self, xy_pairs, xy_pairs_update_flag=None, model:ModelConfig=None, sub_model:ModelConfig=None, x_chunk_length=1000, y_chunk_length=1000):
        self.xy_pairs = xy_pairs
        self.xy_pairs_update_flag = xy_pairs_update_flag or [True] * len(xy_pairs)

        assert len(self.xy_pairs) == len(self.xy_pairs_update_flag), "xy_pairs and xy_pairs_update_flag must be the same length"

        self.model = model
        self.sub_model = sub_model

        self.x_chunk_length = x_chunk_length
        self.y_chunk_length = y_chunk_length

        # x_chunk_length是指一次prompt调用时输入的x长度（由batch_map函数控制）, 此参数会影响到映射到y的扩写率（即：LLM的输出窗口长度/x_chunk_length）
        # 同时，x_chunk_length会影响到map的chunk大小，map的pair大小主要由x_chunk_length决定（具体来说，由update_map函数控制，为x_chunk_length//2)
        # y_chunk_length对pair大小的影响较少（因为映射是一对多）
    
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

    def update_map(self):
        assert len(self.xy_pairs_update_flag) == len(self.xy_pairs), "xy_pairs_update_flag must be the same length as xy_pairs"
        pair_indexes = [i for i, flag in enumerate(self.xy_pairs_update_flag) if flag]

        results = [None] * len(pair_indexes)
        yield_list = [None] * len(pair_indexes)
        finished = [False] * len(pair_indexes)

        generators = [self._update_map(i) for i in pair_indexes]

        first_iter_flag = True
        kp_msg = None
        while True:
            for i, gen in enumerate(generators):
                if finished[i]:
                    continue
                try:
                    yield_list[i] = next(gen)
                except StopIteration as e:
                    results[i] = e.value
                    finished[i] = True
            
            if all(finished):
                break

            if first_iter_flag:
                first_iter_flag = False
                kp_msg = KeyPointMsg(prompt_name='建立映射关系')
                yield kp_msg

            yield [e for e in yield_list if e is not None]

        if kp_msg: yield kp_msg.set_finished()

        # Return the final results
        return [results[i] for i in range(len(results)) if yield_list[i] is not None]

    def _update_map(self, pair_index):
        assert self.xy_pairs_update_flag[pair_index] == True
        x, y = self.xy_pairs[pair_index]

        if not x.strip() and not y.strip():
            self.xy_pairs[pair_index:pair_index+1] = []
            self.xy_pairs_update_flag[pair_index:pair_index+1] = []
            return
        
        x_pair_length, y_pair_length = self.x_chunk_length//2, self.y_chunk_length//2
        
        if not x.strip() or not y.strip():
            if not x.strip():
                new_y_chunks = split_text_into_chunks(y, y_pair_length, min_chunk_n=1)
                self.xy_pairs[pair_index:pair_index+1] = [('', e) for e in new_y_chunks]
                self.xy_pairs_update_flag[pair_index:pair_index+1] = [False] * len(new_y_chunks)
            else:
                new_x_chunks = split_text_into_chunks(x, self.x_chunk_length, min_chunk_n=1)
                self.xy_pairs[pair_index:pair_index+1] = [(e, '') for e in new_x_chunks]
                self.xy_pairs_update_flag[pair_index:pair_index+1] = [False] * len(new_x_chunks)
            return
        
        chunk = self.get_chunk(pair_span=[pair_index, pair_index+1])
        new_x_chunks = split_text_into_chunks(x, x_pair_length, min_chunk_n=1, min_chunk_size=5, max_chunk_n=20)
        new_y_chunks = split_text_into_chunks(y, y_pair_length, min_chunk_n=1, min_chunk_size=5, max_chunk_n=20)

        if len(new_x_chunks) == 1:
            self.xy_pairs_update_flag[pair_index] = False
            return

        if len(new_y_chunks) < len(new_x_chunks):
            new_y_chunks = split_text_into_chunks(y, y_pair_length, min_chunk_n=len(new_x_chunks), min_chunk_size=5, max_chunk_n=20)

        try:
            gen = match_plot_and_text.main(
                model=self.get_sub_model(),
                plot_chunks=new_x_chunks,
                text_chunks=new_y_chunks
                )
            while True:
                yield next(gen), chunk
        except StopIteration as e:
            output = e.value
        
        x2y = output['plot2text']

        new_xy_pairs = []
        for xi_list, yi_list in x2y:
            xl, xr = xi_list[0], xi_list[-1]
            new_xy_pairs.append(("".join(new_x_chunks[xl:xr+1]), "".join(new_y_chunks[i] for i in yi_list)))
        
        pair_span = self.get_chunk_pair_span(chunk) # TODO: update_map需要统一用pair_span进行赋值，另外考虑把flag放入xy_pairs
        assert pair_span[1] - pair_span[0] == 1
        self.xy_pairs[pair_span[0]:pair_span[1]] = new_xy_pairs
        self.xy_pairs_update_flag[pair_span[0]:pair_span[1]] = [False] * len(new_xy_pairs)

        return output, chunk
    
    def get_chunk(self, pair_span=None, x_span=None, y_span=None, context_length=0, smooth=False):
        if sum(x is not None for x in [pair_span, x_span, y_span]) != 1:
            raise ValueError("Exactly one of pair_span, x_span, or y_span must be provided")
        
        assert pair_span is None or (pair_span[0] >= 0 and pair_span[1] <= len(self.xy_pairs)), "pair_span is out of bounds"

        is_x = x_span is not None
        is_pair = pair_span is not None

        if is_pair:
            aligned_span = (
                sum(len(pair[0]) for pair in self.xy_pairs[:pair_span[0]]),
                sum(len(pair[0]) for pair in self.xy_pairs[:pair_span[1]])
            )
            span = aligned_span

            context_pair_span = (
                max(0, pair_span[0] - context_length),
                min(len(self.xy_pairs), pair_span[1] + context_length)
            )
        else:
            span = x_span if is_x else y_span
            full_text = self.x if is_x else self.y

            # Smooth the span if required
            if smooth:
                aligned_span, _ = self.align_span(x_span=span if is_x else None, y_span=span if not is_x else None)
                span = aligned_span

            # Get the aligned span and pair span for the original span
            aligned_span, pair_span = self.align_span(x_span=span if is_x else None, y_span=span if not is_x else None)

            context_span = (max(0, span[0] - context_length), min(len(full_text), span[1] + context_length))
            # Get the aligned span and pair span for the context span
            aligned_context_span, context_pair_span = self.align_span(x_span=context_span if is_x else None, y_span=context_span if not is_x else None)


        # Extract segments and chunks
        x_segment = self.x[span[0]:span[1]] if is_x or is_pair else None
        y_segment = self.y[span[0]:span[1]] if not is_x or is_pair else None

        x_chunk = "".join(pair[0] for pair in self.xy_pairs[pair_span[0]:pair_span[1]])
        y_chunk = "".join(pair[1] for pair in self.xy_pairs[pair_span[0]:pair_span[1]])

        x_chunk_context = "".join(pair[0] for pair in self.xy_pairs[context_pair_span[0]:context_pair_span[1]])
        y_chunk_context = "".join(pair[1] for pair in self.xy_pairs[context_pair_span[0]:context_pair_span[1]])

        # Calculate relative spans
        x_relative_span = (span[0] - aligned_span[0], span[1] - aligned_span[0]) if is_x or is_pair else None
        y_relative_span = (span[0] - aligned_span[0], span[1] - aligned_span[0]) if not is_x or is_pair else None

        return Chunk(
            pair_span=pair_span,
            x_span=span if is_x or is_pair else None,
            y_span=span if not is_x or is_pair else None,
            x_segment=x_segment,
            y_segment=y_segment,
            x_chunk=x_chunk,
            y_chunk=y_chunk,
            x_chunk_context=x_chunk_context,
            y_chunk_context=y_chunk_context,
            x_relative_span=x_relative_span,
            y_relative_span=y_relative_span
        )
    
    def get_chunk_pair_span(self, chunk: Chunk):
        pair_start, pair_end = 0, len(self.xy_pairs)
        for i, (x, y) in enumerate(self.xy_pairs):
            if chunk.x_chunk[:50].startswith(x[:50]) and chunk.y_chunk[:50].startswith(y[:50]):
                pair_start = i
                break

        for i in range(pair_start, len(self.xy_pairs)):
            x, y = self.xy_pairs[i]
            if chunk.x_chunk[-50:].endswith(x[-50:]) and chunk.y_chunk[-50:].endswith(y[-50:]):
                pair_end = i + 1
                break

        # Verify the pair_span
        merged_x_chunk = ''.join(p[0] for p in self.xy_pairs[pair_start:pair_end])
        merged_y_chunk = ''.join(p[1] for p in self.xy_pairs[pair_start:pair_end])
        assert chunk.x_chunk == merged_x_chunk and chunk.y_chunk == merged_y_chunk, "Chunk mismatch"

        return (pair_start, pair_end)

    def apply_chunk(self, chunk: Chunk, key: str, value: str):
        if isinstance(chunk, dict):
            chunk = Chunk(**chunk)

        if key not in ['x_chunk', 'y_chunk', 'x_segment', 'y_segment']:
            raise ValueError("key must be one of 'x_chunk', 'y_chunk', 'x_segment', or 'y_segment'")

        is_x = key.startswith('x')
        chunk_text = chunk.x_chunk if is_x else chunk.y_chunk

        # Convert segment changes to chunk changes
        if key.endswith('segment'):
            relative_span = chunk.x_relative_span if is_x else chunk.y_relative_span
            value = chunk_text[:relative_span[0]] + value + chunk_text[relative_span[1]:]

        # Find and verify the initial pair_span
        pair_start, pair_end = self.get_chunk_pair_span(chunk)

        # Update span based on the verified pair_span
        cumsum = sum(len(self.xy_pairs[i][0] if is_x else self.xy_pairs[i][1]) for i in range(pair_start))
        span = (cumsum, cumsum + len(chunk_text))

        # Detect max edit span and get absolute positions
        if len(chunk_text) > 0:
            l, r = detect_max_edit_span(chunk_text, value)
            edit_span = (span[0] + l, span[0] + len(chunk_text) + r)
            
            if edit_span[0] == edit_span[1]:
                if l == 0:
                    fixed_edit_span = (edit_span[0], edit_span[1] + 1)
                elif r == 0:
                    fixed_edit_span = (edit_span[0] - 1, edit_span[1])
                else:
                    raise ValueError("edit_span must be a single point")
            else:
                fixed_edit_span = edit_span
                
            # Align the span and get the final pair_span
            aligned_edit_span, final_pair_span = self.align_span(x_span=fixed_edit_span if is_x else None,
                                                        y_span=fixed_edit_span if not is_x else None)
            
            assert aligned_edit_span[0] >= span[0] and aligned_edit_span[1] <= span[1], "aligned_edit_span must be in span"
        else:
            l, r = 0, 0
            edit_span = span
            aligned_edit_span = span
            final_pair_span = (pair_start, pair_end)

        # Merge affected pairs
        merged_x = ''.join(p[0] for p in self.xy_pairs[final_pair_span[0]:final_pair_span[1]])
        merged_y = ''.join(p[1] for p in self.xy_pairs[final_pair_span[0]:final_pair_span[1]])

        l2, r2 = edit_span[0] - aligned_edit_span[0], edit_span[1] - aligned_edit_span[1]

        # Apply the edit
        if is_x:
            merged_x = merged_x[:l2] + value[l:r if r != 0 else len(value)] + merged_x[r2 if r2 != 0 else len(merged_x):]
        else:
            merged_y = merged_y[:l2] + value[l:r if r != 0 else len(value)] + merged_y[r2 if r2 != 0 else len(merged_y):]

        # Update xy_pairs
        self.xy_pairs[final_pair_span[0]:final_pair_span[1]] = [(merged_x, merged_y), ]
        if final_pair_span[1] - final_pair_span[0] > 1:
            self.xy_pairs_update_flag[final_pair_span[0]:final_pair_span[1]] = [True, ]

    def batch_map(self, prompt, x_span=None, y_span=None, chunk_length=None, context_length=None, smooth=True, offset=0):
        if not smooth:
            raise ValueError("smooth parameter must be True")
        
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
        pairs = []
        start = aligned_span[0]
        while start < aligned_span[1]:
            if offset > 0:
                end = start + offset
                offset = 0
            else:
                end = start + int(chunk_length * 0.8) # 八二原则，偷个懒，不求最优划分
            end = min(end, aligned_span[1]) 
            chunk_span = (start, end)
            pair = self.get_chunk(x_span=chunk_span if is_x else None, 
                                 y_span=chunk_span if not is_x else None, 
                                 context_length=context_length, 
                                 smooth=True)
            pairs.append(pair)
            start = pair.x_span[1] if is_x else pair.y_span[1]

        if len(pairs) > MAX_THREAD_NUM:
            pairs = pairs[:MAX_THREAD_NUM]
            # TODO: 这里要输出log信息，可以直接用chunk输出也行
            
        # TODO: 限制还是为5，只对前5个chunk进行处理

        # Process all pairs with the prompt and yield intermediate results
        generators = [prompt(pair) for pair in pairs]
        results = [None] * len(pairs)
        yield_list = [None] * len(pairs)
        finished = [False] * len(pairs)
    
        while not all(finished):
            for i, gen in enumerate(generators):
                if finished[i]:
                    continue
                try:
                    yield_value = next(gen)
                    yield_list[i] = (yield_value, pairs[i])
                except StopIteration as e:
                    results[i] = (e.value, pairs[i])
                    finished[i] = True
            
            yield yield_list

        # Return the final results
        return results
    
    # 返回一个更改，对self施加该更改可以变为cur
    def diff_to(self, cur):
        pre_pointer = 0, 1
        cur_pointer = 0, 1

        cum_sum_pre = np.cumsum([0] + [len(pair[0]) for pair in self.xy_pairs])
        cum_sum_cur = np.cumsum([0] + [len(pair[0]) for pair in cur.xy_pairs])

        apply_chunks = []

        while pre_pointer[1] <= len(self.xy_pairs) and cur_pointer[1] <= len(cur.xy_pairs):
            if cum_sum_pre[pre_pointer[1]] - cum_sum_pre[pre_pointer[0]] == cum_sum_cur[cur_pointer[1]] - cum_sum_cur[cur_pointer[0]]:
                chunk = self.get_chunk(pair_span=pre_pointer)
                apply_chunks.append((chunk, 'y_chunk', "".join(pair[1] for pair in cur.xy_pairs[cur_pointer[0]:cur_pointer[1]])))

                pre_pointer = pre_pointer[1], pre_pointer[1] + 1
                cur_pointer = cur_pointer[1], cur_pointer[1] + 1
            elif cum_sum_pre[pre_pointer[1]] - cum_sum_pre[pre_pointer[0]] < cum_sum_cur[cur_pointer[1]] - cum_sum_cur[cur_pointer[0]]:
                pre_pointer = pre_pointer[0], pre_pointer[1] + 1
            else:
                cur_pointer = cur_pointer[0], cur_pointer[1] + 1
        
        assert pre_pointer[1] == len(self.xy_pairs) + 1 and cur_pointer[1] == len(cur.xy_pairs) + 1

        return apply_chunks
    
    def batch_apply(self, prompt_main, user_prompt_text, input_keys=None, x_span=None, y_span=None, chunk_length=None, context_length=None, smooth=True, offset=0, model=None):
        chunk2prompt_key = {
            'x_chunk': 'x',
            'y_chunk': 'y',
            'x_chunk_context': 'context_x',
            'y_chunk_context': 'context_y'
        }
        
        def process_chunk(chunk:Chunk):
            prompt_kwargs = asdict(chunk)
            if input_keys is not None:
                prompt_kwargs = {k: prompt_kwargs[k] for k in input_keys}
                assert all(prompt_kwargs.values()), "Missing required context keys"
            prompt_kwargs = {chunk2prompt_key.get(k, k): v for k, v in prompt_kwargs.items()}
            return prompt_main(
                model=model or self.get_model(),
                user_prompt=user_prompt_text,
                **prompt_kwargs
            )
        
        yield (kp_msg := KeyPointMsg(prompt_name=user_prompt_text))
    
        results = yield from self.batch_map(
            prompt=process_chunk,
            x_span=x_span,
            y_span=y_span,
            chunk_length=chunk_length,
            context_length=context_length,
            smooth=smooth,
            offset=offset
        )

        yield kp_msg.set_finished()

        for output, chunk in results:
            self.apply_chunk(chunk, 'y_chunk', output['text'])

