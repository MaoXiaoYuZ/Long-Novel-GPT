import difflib
from itertools import accumulate
from layers.layer_utils import split_text_into_sentences

def match_span_by_sentence(chunk, text):
    chunk_lines = split_text_into_sentences(chunk)
    text_lines = split_text_into_sentences(text)
    return match_span_by_lines(chunk_lines, text_lines)

def match_span_by_char(chunk, text):
    # 用来存储从text中找到的符合匹配的行的span
    spans = []

    # 使用difflib来寻找最佳匹配行
    matcher = difflib.SequenceMatcher(None, text, chunk)

    # 获取匹配块信息
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            # 记录匹配行的起始和结束索引
            spans.append((i1, i2))
    
    if spans:
        match_span = (spans[0][0], spans[-1][1])
        match_ratio = sum(i2 - i1 for i1, i2 in spans) / len(chunk)
        return match_span, match_ratio
    else:
        return None, 0


def match_span_by_lines(chunk_lines, text_lines):
    # 用来存储从text中找到的符合匹配的行的span
    spans = []

    # 使用difflib来寻找最佳匹配行
    matcher = difflib.SequenceMatcher(None, text_lines, chunk_lines)

    # 获取匹配块信息
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            # 记录匹配行的起始和结束索引
            spans.append((i1, i2))
    
    # 计算字符级别的span
    if spans:
        # 获取行的字符位置
        text_line_starts = [0] + [len(line) + 1 for line in text_lines[:-1]]
        text_line_starts = list(accumulate(text_line_starts))
        
        # 取第一个span的开始和最后一个span的结束
        first_line = spans[0][0]
        last_line = spans[-1][1]
        
        char_start = text_line_starts[first_line]
        char_end = text_line_starts[last_line - 1] + len(text_lines[last_line - 1])
        
        # 计算匹配率
        matched_lines = sum(i2 - i1 for i1, i2 in spans)
        match_ratio = matched_lines / len(chunk_lines)
        
        return (char_start, char_end), match_ratio
    
    return None, 0.0
