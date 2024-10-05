import time
from core.novel_writer import NovelWriter

def load_novel_writer(writer, setting):
    novel_writer = NovelWriter(
        plot=writer['texta'],
        text=writer['textb'],
        plot_text_pairs=writer.get('plot_text_pairs', []),
        model=setting['model'],
        sub_model=setting['sub_model'],
    )
    return novel_writer

def dump_novel_writer(writer, novel_writer, response_messages=None):
    writer['texta'] = novel_writer.plot
    writer['textb'] = novel_writer.text
    writer['plot_text_pairs'] = novel_writer.plot_text_pairs
        
    if response_messages is not None:
        writer['current_cost'] = response_messages.cost
        writer['currency_symbol'] = response_messages.currency_symbol
        writer['total_cost'] += writer['current_cost']


def call_write_all(writer, setting):
    novel_writer = load_novel_writer(writer, setting)
    generator = novel_writer.init_text()
    while True:
        try:
            output = next(generator)
            cost_info = f"(预计花费：{output['response_msgs'].cost:.4f}{output['response_msgs'].currency_symbol})"
            if 'plot2text' in output:
                yield f"正在建立剧情和正文的映射关系..." + cost_info
            else:
                yield output['text'] + cost_info
        except StopIteration as e:
            novel_writer.set_output(e.value)
            dump_novel_writer(writer, novel_writer, output['response_msgs'])
            writer['textb'] = e.value
            return e.value


def call_rewrite_suggestion(writer, pair, setting):
    novel_writer = load_novel_writer(writer, setting)
    generator = novel_writer.generate_rewrite_suggestion(pair['a_source_index'])
    while True:
        try:
            output = next(generator)
            cost_info = f"(预计花费：{output['response_msgs'].cost:.4f}{output['response_msgs'].currency_symbol})"
            if 'plot2text' in output:
                yield f"正在建立剧情和正文的映射关系..." + cost_info
            else:
                yield output['suggestion'] + cost_info
        except StopIteration as e:
            pair['suggestion_win']['output_suggestion'] = e.value
            dump_novel_writer(writer, novel_writer, output['response_msgs'])
            return e.value


def call_rewrite_text(writer, pair, setting):
    novel_writer = load_novel_writer(writer, setting)
    suggestion = pair['suggestion_win']['output_suggestion']
    selected_span = pair['a_source_index']
    generator = novel_writer.generate_rewrite_text(suggestion, selected_span)
    while True:
        try:
            output = next(generator)
            cost_info = f"(预计花费：{output['response_msgs'].cost:.4f}{output['response_msgs'].currency_symbol})"
            if 'plot2text' in output:
                yield f"正在建立剧情和正文的映射关系..." + cost_info
            else:
                yield output['text'] + cost_info
        except StopIteration as e:
            pair['text_win']['output_text'] = e.value
            pair['b'] = e.value
            dump_novel_writer(writer, novel_writer, output['response_msgs'])
            return e.value


def call_accept(writer, pair, setting):
    novel_writer = load_novel_writer(writer, setting)
    
    textb = writer['textb']
    a_source_index = pair['a_source_index']
    start, end = a_source_index
    new_text = textb[:start] + pair['b'] + textb[end:]

    novel_writer.set_output(new_text)
    writer['textb'] = new_text
    
    dump_novel_writer(writer, novel_writer)
    return new_text