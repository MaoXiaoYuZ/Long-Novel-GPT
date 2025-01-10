import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.parser_utils import parse_chapters
from core.summary_novel import summary_draft, summary_plot, summary_chapters
from prompts.prompt_utils import load_text
from llm_api import ModelConfig
from rich.live import Live
from rich.table import Table
from rich import box
from rich.console import Console


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

def create_progress_table(yields):
    table = Table(box=box.MINIMAL)
    table.add_column("Progress")
    for item in yields:
        if item is not None:
            table.add_row(item)
    return table

# 创建一个控制台对象
console = Console()

model = ModelConfig(model='glm-4-plus', api_key='68225a7a158bd3674bf07edbd248d620.15paBYrpUn0o8Dvi', max_tokens=4000)
sub_model = ModelConfig(model='glm-4-flashx', api_key='68225a7a158bd3674bf07edbd248d620.15paBYrpUn0o8Dvi', max_tokens=4000)

novel_text = load_text("data/斗破苍穹.txt", 100_000)

chapter_titles, chapter_contents = parse_chapters(novel_text)


with Live(refresh_per_second=4) as live:
    dw_list = []
    gens = [summary_draft(model, sub_model, ' '.join(title), content) for title, content in zip(chapter_titles, chapter_contents)]
    for yields in batch_yield(gens, ret=dw_list):
        table = create_progress_table([y for y in yields if y is not None])
        live.update(table)
    
    cw_list = []
    gens = [summary_plot(model, sub_model, ' '.join(title), dw.x) for title, dw in zip(chapter_titles, dw_list)]
    for yields in batch_yield(gens, ret=cw_list):
        table = create_progress_table([y for y in yields if y is not None])
        live.update(table)


    ow_list = []
    gens = [summary_chapters(model, sub_model, '斗破', chapter_titles, [cw.global_context['chapter'] for cw in cw_list])]
    for yields in batch_yield(gens, ret=ow_list):
        table = create_progress_table([y for y in yields if y is not None])
        live.update(table)
