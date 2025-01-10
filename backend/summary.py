import time
from core.parser_utils import parse_chapters
from core.summary_novel import summary_draft, summary_plot, summary_chapters
from config import MAX_NOVEL_SUMMARY_LENGTH, MAX_THREAD_NUM, ENABLE_ONLINE_DEMO

def batch_yield(generators, max_co_num=5, ret=[]):
    results = [None] * len(generators)
    yields = [None] * len(generators)
    finished = [False] * len(generators)

    while True:
        co_num = 0
        for i, gen in enumerate(generators):
            if finished[i]:
                continue

            try:
                co_num += 1
                yield_value = next(gen)
                yields[i] = yield_value
            except StopIteration as e:
                results[i] = e.value
                finished[i] = True
            
            if co_num >= max_co_num:
                    break
        
        if all(finished):
            break

        yield yields

    ret.clear()
    ret.extend(results)
    return ret

def process_novel(content, novel_name, model, sub_model, max_novel_summary_length, max_thread_num):
    if ENABLE_ONLINE_DEMO:
        if max_novel_summary_length > MAX_NOVEL_SUMMARY_LENGTH:
            raise Exception("在线Demo模型下，最大小说长度不能超过" + str(MAX_NOVEL_SUMMARY_LENGTH) + "个字符！")
        if max_thread_num > MAX_THREAD_NUM:
            raise Exception("在线Demo模型下，最大线程数不能超过" + str(MAX_THREAD_NUM) + "！")

    if len(content) > max_novel_summary_length:
        content = content[:max_novel_summary_length]
        yield {"progress_msg": f"小说长度超出最大处理长度，已截断，只处理前{max_novel_summary_length}个字符。"}
        time.sleep(1)

    # Parse chapters
    yield {"progress_msg": "正在解析章节..."}

    chapter_titles, chapter_contents = parse_chapters(content)

    yield {"progress_msg": "解析出章节数：" + str(len(chapter_titles))}

    if len(chapter_titles) == 0:
        raise Exception("解析出章节数为0！！！")

    # Process draft summaries
    yield {"progress_msg": "正在生成剧情摘要..."}
    dw_list = []
    gens = [summary_draft(model, sub_model, ' '.join(title), content) for title, content in zip(chapter_titles, chapter_contents)]
    for yields in batch_yield(gens, ret=dw_list, max_co_num=max_thread_num):
        chars_num = sum([e['chars_num'] for e in yields if e is not None])
        current_cost = sum([e['current_cost'] for e in yields if e is not None])
        currency_symbol = next(e['currency_symbol'] for e in yields if e is not None)
        model_text = next(e['model'] for e in yields if e is not None)
        yield {"progress_msg": f"正在生成剧情摘要 进度：{sum([1 for e in yields if e is not None])} / {len(yields)} 模型：{model_text} 已生成字符：{chars_num} 已花费：{current_cost:.4f}{currency_symbol}"}

    # Process plot summaries
    yield {"progress_msg": "正在生成章节大纲..."}
    cw_list = []
    gens = [summary_plot(model, sub_model, ' '.join(title), dw.x) for title, dw in zip(chapter_titles, dw_list)]
    for yields in batch_yield(gens, ret=cw_list, max_co_num=max_thread_num):
        chars_num = sum([e['chars_num'] for e in yields if e is not None])
        current_cost = sum([e['current_cost'] for e in yields if e is not None])
        currency_symbol = next(e['currency_symbol'] for e in yields if e is not None)
        model_text = next(e['model'] for e in yields if e is not None)
        yield {"progress_msg": f"正在生成章节大纲 进度：{sum([1 for e in yields if e is not None])} / {len(yields)} 模型：{model_text} 已生成字符：{chars_num} 已花费：{current_cost:.4f}{currency_symbol}"}

    # Process chapter summaries
    yield {"progress_msg": "正在生成全书大纲..."}
    ow_list = []
    gens = [summary_chapters(model, sub_model, novel_name, chapter_titles, [cw.global_context['chapter'] for cw in cw_list])]
    for yields in batch_yield(gens, ret=ow_list, max_co_num=max_thread_num):
        chars_num = sum([e['chars_num'] for e in yields if e is not None])
        current_cost = sum([e['current_cost'] for e in yields if e is not None])
        currency_symbol = next(e['currency_symbol'] for e in yields if e is not None)
        model_text = next(e['model'] for e in yields if e is not None)
        yield {"progress_msg": f"正在生成全书大纲 模型：{model_text} 已生成字符：{chars_num} 已花费：{current_cost:.4f}{currency_symbol}"}

    # Prepare final response
    outline = ow_list[0]
    plot_data = {}
    draft_data = {}

    for title, chapter_outline, cw, dw in zip(chapter_titles, [e[1] for e in outline.xy_pairs], cw_list, dw_list):
        chapter_name = ' '.join(title)
        plot_data[chapter_name] = {
            'chunks': [('', e) for e, _ in dw.xy_pairs],
            'context': chapter_outline # 不采用cw.global_context['chapter']，因为不含章节名
        }
        draft_data[chapter_name] = {
            'chunks': dw.xy_pairs,
            'context': ''  # Draft doesn't have global context
        }

    final_response = {
        "progress_msg": "处理完成！",
        "outline": {
            "chunks": outline.xy_pairs,
            "context": outline.global_context['outline']
        },
        "plot": plot_data,
        "draft": draft_data
    }

    yield final_response
