import numpy as np
from core.draft_writer import DraftWriter
from core.plot_writer import PlotWriter
from core.outline_writer import OutlineWriter
from core.writer_utils import KeyPointMsg



def summary_draft(model, sub_model, chapter_title, chapter_text):
    xy_pairs = [('', chapter_text)]

    dw = DraftWriter(xy_pairs, {}, model=model, sub_model=sub_model, x_chunk_length=500, y_chunk_length=1000)
    dw.max_thread_num = 1   # 每章的处理只采用一个线程

    generator = dw.summary(pair_span=(0, len(xy_pairs)))

    kp_msg_title = ''
    for kp_msg in generator:
        if isinstance(kp_msg, KeyPointMsg):
            # 如果要支持关键节点保存，需要计算一个编辑上的更改，然后在这里yield writer
            kp_msg_title = kp_msg.prompt_name
            continue
        else:
            chunk_list = kp_msg

        current_cost = 0
        currency_symbol = ''
        finished_chunk_num = 0
        chars_num = 0
        model = None
        for e in chunk_list:
            if e is None: continue
            finished_chunk_num += 1
            output, chunk = e
            if output is None: continue #  说明是map_text, 在第一次next就stop iteration了
            current_cost += output['response_msgs'].cost
            currency_symbol = output['response_msgs'].currency_symbol
            chars_num += len(output['response_msgs'].response)
            model = output['response_msgs'].model

        yield dict(
            progress_msg=f"[{chapter_title}] 提炼章节剧情 {kp_msg_title} 进度：{finished_chunk_num}/{len(chunk_list)}  已创作字符：{chars_num}  已花费：{current_cost:.4f}{currency_symbol}",
            chars_num=chars_num,
            current_cost=current_cost,
            currency_symbol=currency_symbol,
            model=model
        )

    return dw


def summary_plot(model, sub_model, chapter_title, chapter_plot):
    xy_pairs = [('', chapter_plot)]
    
    pw = PlotWriter(xy_pairs, {}, model=model, sub_model=sub_model, x_chunk_length=500, y_chunk_length=1000)
    
    generator = pw.summary()

    for output in generator:
        current_cost = output['response_msgs'].cost
        currency_symbol = output['response_msgs'].currency_symbol
        chars_num = len(output['response_msgs'].response)
        yield dict(
            progress_msg=f"[{chapter_title}] 提炼章节大纲 已创作字符：{chars_num}  已花费：{current_cost:.4f}{currency_symbol}",
            chars_num=chars_num,
            current_cost=current_cost,
            currency_symbol=currency_symbol,
            model=output['response_msgs'].model
        )

    return pw

def summary_chapters(model, sub_model, title, chapter_titles, chapter_content):
    ow = OutlineWriter([('', '')], {}, model=model, sub_model=sub_model, x_chunk_length=500, y_chunk_length=1000)
    ow.xy_pairs = ow.construct_xy_pairs(chapter_titles, chapter_content)
    
    generator = ow.summary()

    for output in generator:
        current_cost = output['response_msgs'].cost
        currency_symbol = output['response_msgs'].currency_symbol
        chars_num = len(output['response_msgs'].response)
        yield dict(
            progress_msg=f"[{title}] 提炼全书大纲 已创作字符：{chars_num}  已花费：{current_cost:.4f}{currency_symbol}",
            chars_num=chars_num,
            current_cost=current_cost,
            currency_symbol=currency_symbol,
            model=output['response_msgs'].model
        )

    return ow


    