import uuid

# 定义了用于Wirter yield的数据类型，同时也是前端展示的“关键点”消息
class KeyPointMsg(dict):
    def __init__(self, title='', subtitle='', prompt_name=''):
        super().__init__()
        if not title and not subtitle and prompt_name:
            pass
        elif title and subtitle and not prompt_name:
            pass
        else:
            raise ValueError('Either title and subtitle or prompt_name must be provided')
        
        self.update({
            'id': str(uuid.uuid4()),
            'title': title,
            'subtitle': subtitle,
            'prompt_name': prompt_name,
            'finished': False
        })

    def set_finished(self):
        assert not self['finished'], 'finished flag is already set'
        self['finished'] = True
        return self # 返回self，方便链式调用

    def is_finished(self):
        return self['finished']
    
    def is_prompt(self):
        return bool(self.prompt_name)
    
    def is_title(self):
        return bool(self.title)
    
    @property
    def id(self):
        return self['id']
    
    @property
    def title(self):
        return self['title']
    
    @property
    def subtitle(self):
        return self['subtitle']
    
    @property
    def prompt_name(self):
        prompt_name = self['prompt_name']
        if len(prompt_name) >= 10:
            return prompt_name[:10] + '...'
        return prompt_name


import re
from difflib import Differ

# 后续考虑采用现成的库实现，目前逻辑过于繁琐，而且太慢了
def detect_max_edit_span(a, b):
    diff = Differ().compare(a, b)

    l = 0
    r = 0
    flag_count_l = True

    for tag in diff:
        if tag.startswith(' '):
            if flag_count_l:
                l += 1
            else:
                r += 1
        else:
            flag_count_l = False
            r = 0

    return l, -r   

def split_text_by_separators(text, separators, keep_separators=True):
    """
    将文本按指定的分隔符分割为段落
    Args:
        text: 要分割的文本
        separators: 分隔符列表
        keep_separators: 是否在结果中保留分隔符，默认为True
    Returns:
        包含分割后段落的列表
    """
    pattern = f'({"|".join(map(re.escape, separators))}+)'
    chunks = re.split(pattern, text)
    
    paragraphs = []
    current_para = []
    
    for i in range(0, len(chunks), 2):
        content = chunks[i]
        separator = chunks[i + 1] if i + 1 < len(chunks) else ''
        
        current_para.append(content)
        if keep_separators and separator:
            current_para.append(separator)
            
        if content.strip():
            paragraphs.append(''.join(current_para))
            current_para = []
    
    return paragraphs

def split_text_into_paragraphs(text, keep_separators=True):
    return split_text_by_separators(text, ['\n'], keep_separators)

def split_text_into_sentences(text, keep_separators=True):
    return split_text_by_separators(text, ['\n', '。', '？', '！', '；'], keep_separators)

def run_and_echo_yield_func(func, *args, **kwargs):
    echo_text = ""
    all_messages = []
    for messages in func(*args, **kwargs):
        all_messages.append(messages)
        new_echo_text = "\n".join(f"{msg['role']}:\n{msg['content']}" for msg in messages)
        if new_echo_text.startswith(echo_text):
            delta_echo_text = new_echo_text[len(echo_text):]
        else:
            echo_text = ""
            print('\n--------------------------------')
            delta_echo_text = new_echo_text

        print(delta_echo_text, end="")
        echo_text = echo_text + delta_echo_text
    return all_messages

def run_yield_func(func, *args, **kwargs):
    gen = func(*args, **kwargs)
    try:
        while True:
            next(gen)
    except StopIteration as e:
        return e.value

def split_text_into_chunks(text, max_chunk_size, min_chunk_n, min_chunk_size=1, max_chunk_n=1000):
    def split_paragraph(para):
        mid = len(para) // 2
        split_pattern = r'[。？；]'
        split_points = [m.end() for m in re.finditer(split_pattern, para)]
        
        if not split_points:
            raise Exception("没有找到分割点!")
        
        closest_point = min(split_points, key=lambda x: abs(x - mid))
        if not para[:closest_point].strip() or not para[closest_point:].strip():
            raise Exception("没有找到分割点!")
        
        return para[:closest_point], para[closest_point:]

    paragraphs = split_text_into_paragraphs(text)

    assert max_chunk_n >= 1, "max_chunk_n必须大于等于1"
    assert sum(len(p) for p in paragraphs) >= min_chunk_size, f"分割时，输入的文本长度小于要求的min_chunk_size:{min_chunk_size}"
    count = 0 # 防止死循环
    while len(paragraphs) > max_chunk_n or min(len(p) for p in paragraphs) < min_chunk_size:
        assert (count:=count+1) < 1000, "分割进入死循环！"

        # 找出相邻chunks中和最小的两个进行合并
        min_sum = float('inf')
        min_i = 0

        for i in range(len(paragraphs) - 1):
            curr_sum = len(paragraphs[i]) + len(paragraphs[i + 1])
            if curr_sum < min_sum:
                min_sum = curr_sum
                min_i = i
                
        # 合并这两个chunks
        paragraphs[min_i:min_i + 2] = [''.join(paragraphs[min_i:min_i + 2])]

    while len(paragraphs) < min_chunk_n or max(len(p) for p in paragraphs) > max_chunk_size:
        assert (count:=count+1) < 1000, "分割进入死循环！"
        longest_para_i = max(range(len(paragraphs)), key=lambda i: len(paragraphs[i]))
        part1, part2 = split_paragraph(paragraphs[longest_para_i])
        if len(part1) < min_chunk_size or len(part2) < min_chunk_size or len(paragraphs) + 1 > max_chunk_n:
            raise Exception("没有找到合适的分割点!")
        paragraphs[longest_para_i:longest_para_i+1] = [part1, part2]
    
    return paragraphs

def test_split_text_into_chunks():
    # Test case 1: Simple paragraph splitting
    text1 = "这是第一段。这是第二段。这是第三段。"
    result1 = split_text_into_chunks(text1, max_chunk_size=10, min_chunk_n=3)
    print("Test 1 result:", result1)
    assert len(result1) == 3, f"Expected 3 chunks, got {len(result1)}"


    # Test case 2: Long paragraph splitting
    text2 = "这是一个很长的段落，包含了很多句子。它应该被分割成多个小块。这里有一些标点符号，比如句号。还有问号？以及分号；这些都可以用来分割文本。"
    result2 = split_text_into_chunks(text2, max_chunk_size=20, min_chunk_n=4)
    print("Test 2 result:", result2)
    assert len(result2) >= 4, f"Expected at least 4 chunks, got {len(result2)}"
    assert all(len(chunk) <= 20 for chunk in result2), "Some chunks are longer than max_chunk_size"

    # Test case 3: Text with newlines
    text3 = "第一段。\n\n第二段。\n第三段。\n\n第四段很长，需要被分割。这是第四段的继续。"
    result3 = split_text_into_chunks(text3, max_chunk_size=15, min_chunk_n=5)
    print("Test 3 result:", result3)
    assert len(result3) >= 5, f"Expected at least 5 chunks, got {len(result3)}"
    assert all(len(chunk) <= 15 for chunk in result3), "Some chunks are longer than max_chunk_size"

    print("All tests passed!")

if __name__ == "__main__":
    print(detect_max_edit_span("我吃西红柿", "我不喜欢吃西红柿"))
    print(detect_max_edit_span("我吃西红柿", "不喜欢吃西红柿"))
    print(detect_max_edit_span("我吃西红柿", "我不喜欢吃"))
    print(detect_max_edit_span("我吃西红柿", "你不喜欢吃西瓜"))

    test_split_text_into_chunks()
