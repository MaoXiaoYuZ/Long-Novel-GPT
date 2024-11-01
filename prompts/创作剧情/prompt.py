import os
from prompts.baseprompt import main as base_main



def main(model, user_prompt, **kwargs):
    dirname = os.path.dirname(__file__)

    if 'context_y' in kwargs and 'y' in kwargs and kwargs['context_y'] == kwargs['y']:
        kwargs['context_y'] = '参考**剧情**'

    if 'context_x' in kwargs and 'x' in kwargs and kwargs['context_x'] == kwargs['x']:
        kwargs['context_x'] = '参考**大纲**'
    
    ret = yield from base_main(model, dirname, user_prompt, **kwargs)

    return ret



