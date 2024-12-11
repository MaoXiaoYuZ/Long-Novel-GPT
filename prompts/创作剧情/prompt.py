import os
from prompts.baseprompt import main as base_main
from core.writer_utils import split_text_into_sentences

def format_plot(text):
    text = text.replace('\n', '')
    sentences = split_text_into_sentences(text, keep_separators=True)
    return "\n".join(sentences)

def main(model, user_prompt, **kwargs):
    dirname = os.path.dirname(__file__)

    if 'context_y' in kwargs and 'y' in kwargs and kwargs['context_y'] == kwargs['y']:
        kwargs['context_y'] = '参考**剧情**'

    if 'context_x' in kwargs and 'x' in kwargs and kwargs['context_x'] == kwargs['x']:
        kwargs['context_x'] = '参考**章节大纲**'
    
    for ret in base_main(model, dirname, user_prompt, **kwargs):
        # ret['text'] = format_plot(ret['text'])
        yield ret

    return ret



