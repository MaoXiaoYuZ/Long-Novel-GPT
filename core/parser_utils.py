import re


def parse_chapters(content):
    # Single pattern to capture: full chapter number (第X章), title, and content
    pattern = r'(第[零一二三四五六七八九十百千万亿0123456789.-]+章)([^\n]*)\n*([\s\S]*?)(?=第[零一二三四五六七八九十百千万亿0123456789.-]+章|$)'
    matches = re.findall(pattern, content)
    
    # Unpack directly into separate lists using zip
    chapter_titles, title_names, chapter_contents = zip(*[
        (index, name.strip(), content.strip())
        for index, name, content in matches
    ]) if matches else ([], [], [])
    
    return list(zip(chapter_titles, title_names)), list(chapter_contents)


if __name__ == "__main__":
    test = """
    第1-1章 出世
    主角张小凡出身贫寒，因天赋异禀被青云门收为弟子，开始修仙之路。

    第2.1章 初入青云

    张小凡在青云门中结识师兄弟，学习基础法术，逐渐适应修仙生活。

    第3章 灵气初现
    张小凡在一次意外中感受到天地灵气，修为有所提升。
    """

    results = parse_chapters(test)
    print()
