from promptflow.client import load_flow

from demo.main_chat_messages import yield_join

import os, time
import json


def run_prompt(source, **kwargs):
    flow = load_flow(source=source)

    log_file_path = os.path.join(source, '.promptflow', f'flow_run_log.jsonl')
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    with open(log_file_path, 'a', encoding='utf-8') as f:
        json.dump(kwargs, f, ensure_ascii=False)
        f.write('\n')

    result = yield from yield_join(flow, **kwargs)

    return result

def run_prompt_no_echo(source, **kwargs):
    flow = load_flow(source=source)

    return flow(**kwargs)