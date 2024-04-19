from os import path
from promptflow.core import tool, load_flow

import sys, os
root_path = os.path.abspath(os.path.join(os.path.abspath(__file__), "../.."))
if root_path not in sys.path:
    sys.path.append(root_path)


@tool
def polish(messages, context, model, config, text):
    source = path.join(path.dirname(path.abspath(__file__)), "./polish")
    flow = load_flow(source=source)

    return flow(
        chat_messages=messages,
        context=context,
        model=model,
        config=config,
        text=text,
        )

 