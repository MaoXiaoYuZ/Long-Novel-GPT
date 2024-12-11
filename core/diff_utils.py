import difflib
from difflib import SequenceMatcher


def match_span_by_char(text, chunk):
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

def match_sequences(a_list, b_list):
    """
    匹配两个字符串列表，返回匹配的索引对
    
    Args:
        a_list: 第一个字符串列表
        b_list: 第二个字符串列表
    
    Returns:
        list[((l,r), (j,k))]: 匹配的索引对列表，
        其中(l,r)表示a_list的起始和结束索引，(j,k)表示b_list的起始和结束索引
    """
    m, n = len(a_list) - 1, len(b_list) - 1
    matches = []
    i = j = 0
    
    while i < m and j < n:
        # 初始化当前最佳匹配
        best_match = None
        best_ratio = -1  # 设置匹配阈值
        
        # 尝试从当前位置开始的不同组合
        for l in range(i, min(i + 3, m)):  # 限制向前查找的范围
            current_a = ''.join(a_list[i:l + 1])
            
            for r in range(j, min(j + 3, n)):  # 限制向前查找的范围
                current_b = ''.join(b_list[j:r + 1])
                
                # 使用已有的match_span_by_char函数计算匹配度
                span1, ratio1 = match_span_by_char(current_b, current_a)
                span2, ratio2 = match_span_by_char(current_a, current_b)
                ratio = ratio1 * ratio2

                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = ((i, l + 1), (j, r + 1))
        
        if best_match:
            matches.append(best_match)
            i = best_match[0][1]
            j = best_match[1][1]
        else:
            # 如果没找到好的匹配，向前移动一步
            i += 1
            j += 1
    
    matches.append(((i, m+1), (j, n+1)))
    
    return matches

def get_chunk_changes(source_chunk_list, target_chunk_list):
    SEPARATOR = "%|%"
    source_text = SEPARATOR.join(source_chunk_list)
    target_text = SEPARATOR.join(target_chunk_list)
    
    # 初始化每个chunk的tag统计
    source_chunk_stats = [{'delete_or_insert': 0, 'replace_or_equal': 0} for _ in source_chunk_list]
    target_chunk_stats = [{'delete_or_insert': 0, 'replace_or_equal': 0} for _ in target_chunk_list]
    
    # 获取chunk的起始位置列表
    source_positions = [0]
    target_positions = [0]
    pos = 0
    for chunk in source_chunk_list[:-1]:
        pos += len(chunk) + len(SEPARATOR)
        source_positions.append(pos)
    source_positions.append(len(source_text))
    
    pos = 0
    for chunk in target_chunk_list[:-1]:
        pos += len(chunk) + len(SEPARATOR)
        target_positions.append(pos)
    target_positions.append(len(target_text))
    
    def update_chunk_stats(positions, stats, start, end, tag):
        for i in range(len(positions) - 1):
            chunk_start = positions[i]
            chunk_end = positions[i + 1]
            
            overlap_start = max(chunk_start, start)
            overlap_end = min(chunk_end, end)
            
            if overlap_end > overlap_start:
                stats[i][tag] += overlap_end - overlap_start
    
    matcher = SequenceMatcher(None, source_text, target_text)
    
    # 处理每个操作块并更新统计信息
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'replace' or tag == 'equal':
            update_chunk_stats(source_positions, source_chunk_stats, i1, i2, 'replace_or_equal')
            update_chunk_stats(target_positions, target_chunk_stats, j1, j2, 'replace_or_equal')
        elif tag == 'delete':
            update_chunk_stats(source_positions, source_chunk_stats, i1, i2, 'delete_or_insert')
        elif tag == 'insert':
            update_chunk_stats(target_positions, target_chunk_stats, j1, j2, 'delete_or_insert')
    
    # 确定每个chunk的最终tag
    def get_final_tag(stats):
        return 'delete_or_insert' if stats['delete_or_insert'] > stats['replace_or_equal'] else 'replace_or_equal'
    
    source_chunk_tags = [get_final_tag(stats) for stats in source_chunk_stats]
    target_chunk_tags = [get_final_tag(stats) for stats in target_chunk_stats]
    
    # 使用双指针计算changes
    changes = []
    i = j = 0  # i指向source_chunk_list，j指向target_chunk_list
    start_i = start_j = 0
    m, n = len(source_chunk_list), len(target_chunk_list)
    while i < m or j < n:
        if i < m and source_chunk_tags[i] == 'delete_or_insert':
            while i < m and source_chunk_tags[i] == 'delete_or_insert': i += 1
        elif j < n and target_chunk_tags[j] == 'delete_or_insert':
            while j < n and target_chunk_tags[j] == 'delete_or_insert': j += 1
        elif i < m and j < n and source_chunk_tags[i] == 'replace_or_equal' and target_chunk_tags[j] == 'replace_or_equal':
            while i < m and j < n and source_chunk_tags[i] == 'replace_or_equal' and target_chunk_tags[j] == 'replace_or_equal':
                i += 1
                j += 1
        else:
            # TODO: 这个算法目前还有一些问题，即equal的对应
            break
            
        # 当有任意一个指针移动时，检查是否需要添加change
        if (i > start_i or j > start_j):
            changes.append((start_i, i, start_j, j))
            start_i, start_j = i, j
    
    if (i < m or j < n):
        changes.append((start_i, m, start_j, n))

    return changes


# 使用示例
def test_get_chunk_changes():
    source_chunks = ['', '', '', '第3章 初露锋芒\n在高人指导下，萧炎的斗气水平迅速提升，开始在家族中引起注意。\n', '',  '第4章 异火初现\n萧炎得知“异火”的存在，决定踏上寻找异火的旅程。\n']
    target_chunks = ['', '第3章 初露锋芒\n在高人指导下，萧炎的斗气水平迅速提升，开始在家族中引起注意。', '第3.5章 家族试炼\n萧炎参加家族举办的试炼，凭借新学的斗技和炼丹术，展现出超凡实力，获得家族长老的关注和认可。', '第4章 异火初现\n萧炎得知“异火”的存在，决定踏上寻找异火的旅程。']

    changes = get_chunk_changes(source_chunks, target_chunks)
    for change in changes:
        print(f"Source chunks {change[0]}:{change[1]} -> Target chunks {change[2]}:{change[3]}")


    for change in changes:
        print('-' * 20)
        print(f"{''.join(source_chunks[change[0]:change[1]])} -> {''.join(target_chunks[change[2]:change[3]])}")

if __name__ == "__main__":
    test_get_chunk_changes()