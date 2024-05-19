import re
from difflib import Differ


def detect_max_edit_span(a, b):
    diff = Differ().compare(a, b)

    l = 0
    r = 0
    flag_count_l = True

    for tag in diff:
        if tag.startswith(' '):
            if flag_count_l:
                l += 1
            r += 1
        else:
            flag_count_l = False
            r = 0

    return l, -r   

def split_text_into_paragraphs(text):
    chunks = re.split(r'(\n+)', text)
    assert len(chunks) % 2 == 1, "split结果不为奇数"

    chunks.append("")
    paragraphs = []
    para = []
    for chunk, separator in zip(chunks[::2], chunks[1::2]):
        para.append(chunk)
        para.append(separator)
        if chunk.strip():
            paragraphs.append("".join(para))
            para.clear()
        else:
            continue
     
    return paragraphs

def run_and_echo_yield_func(func, *args, **kwargs):
    echo_text = ""
    all_messages = []
    for messages in func(*args, **kwargs):
        all_messages.append(messages)
        new_echo_text = "".join(f"{msg['role']}:\n{msg['content']}\n" for msg in messages)
        if new_echo_text.startswith(echo_text):
            delta_echo_text = new_echo_text[len(echo_text):]
        else:
            echo_text = ""
            print('\n--------------------------------')
            delta_echo_text = new_echo_text

        print(delta_echo_text, end="")
        echo_text = echo_text + delta_echo_text
    return all_messages

if __name__ == "__main__":
    print(detect_max_edit_span("我吃西红柿", "我不喜欢吃西红柿"))
    print(detect_max_edit_span("我吃西红柿", "不喜欢吃西红柿"))
    print(detect_max_edit_span("我吃西红柿", "我不喜欢吃"))
    print(detect_max_edit_span("我吃西红柿", "你不喜欢吃西瓜"))