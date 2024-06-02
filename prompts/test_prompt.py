import json
import sys, os
root_path = os.path.abspath(os.path.join(os.path.abspath(__file__), "../.."))
sys.path.append(root_path)

from prompts.load_utils import run_prompt

def json_load(input_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        if input_file.endswith('.jsonl'):
            return [json.loads(line) for line in f.readlines()]
        else:
            return json.load(f)


if __name__ == "__main__":
    path = "./prompts/创作正文"
    kwargs = json_load(os.path.join(path, 'data.jsonl'))[0]

    gen = run_prompt(source=path, **kwargs)

    list(gen)