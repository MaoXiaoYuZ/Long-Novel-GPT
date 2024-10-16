import gradio as gr
import time



xy_pairs = [
    [
    "李珣呆立不动，背后传来水声，那雾中的女子在悠闲洗浴。\n\n",
    "李珣呆立在原地，一动不动。他听到背后传来的水声，潺潺如溪，那是雾中的女子在悠闲地洗浴。这个场景对他来说太过意外，他心中充满了震惊，这样的女子，绝非普通人。\n\n"
    ],
    [
    "她随后淡然问话，李珣感到对方危险可怕。\n\n",
    "在朦胧的月光下，她缓缓地开了口，声音平静而淡然，仿佛带着一种不易察觉的威胁。李珣在她面前感到前所未有的压迫感，仿佛自己正面对着一个深藏不露的高手，这让他心生警惕，觉得对方既危险又可怕。\n\n"
    ],
    [
    "她询问李珣怎么上山，李珣答“爬上来的”，这让对方略显惊讶。\n\n",
    "“你是怎么上来的？”她问，目光如炬地盯着李珣。\n\n“爬上来的。”李珣回答得有些艰难，但尽量保持镇定。他的话让对方轻轻挑了挑眉，似乎对这个答案略感惊讶。\n\n"
    ],
    [
    "女子探问他身，李珣庆幸自己内息如同名门，为保命决定实话实说，自报身份并讲述过往经历，隐去危险细节。\n\n",
    "女子没有立即回应，只是用那双深邃的眼睛打量着李珣，仿佛要看穿他的灵魂。片刻后，她再次开口，声音依旧平静：“你是谁？为什么会在这里？”\n\n李珣深吸了一口气，他知道自己必须小心应对。他庆幸自己的内息修炼得如同名门正派，这让他在面对盘问时有了一定的底气。为了保命，他决定实话实说，但也要谨慎地隐去那些可能危及他性命的细节。\n\n“我叫李珣，”他开口，声音略显沙哑，“我是个江湖浪人，因为一些缘故被人追杀，逃到了这里。我曾是某个小派的弟子，但因得罪了权贵，被迫离开了师门。这些年来，我一直在江湖上漂泊，历练自己，希望能有朝一日洗清冤屈，重回师门。”\n\n他的话语中透露出一丝无奈和坚定，女子听后没有说话，只是静静地看着他，似乎在判断他话中的真假。李珣也紧张地看着她，等待她的回应。\n"
    ],
    [
    "尽管转身，他仍紧闭眼睛，慌乱道歉。\n\n",
    "“对不起，我……我不知道你在这里。”他慌乱地道歉，声音中带着几分颤抖。\n\n"
    ]
    ]


def create_comparison_table(pairs, column_names=['Original Text', 'Enhanced Text', 'Enhanced Text 2']):
    # Check if any pair has 3 elements
    has_third_column = any(len(pair) == 3 for pair in pairs)
    
    # Create table header
    if has_third_column:
        table = f"| {column_names[0]} | {column_names[1]} | {column_names[2]} |\n|---------------|-----------------|----------------|\n"
    else:
        table = f"| {column_names[0]} | {column_names[1]} |\n|---------------|---------------|\n"
    
    # Add rows to the table
    for pair in pairs:
        x = pair[0].replace('|', '\\|').replace('\n', '<br>')
        y1 = pair[1].replace('|', '\\|').replace('\n', '<br>')
        
        if has_third_column:
            y2 = pair[2].replace('|', '\\|').replace('\n', '<br>') if len(pair) == 3 else ''
            table += f"| {x} | {y1} | {y2} |\n"
        else:
            table += f"| {x} | {y1} |\n"
    
    return table


with gr.Blocks() as demo:
    gr.Markdown("# Text Comparison")
    comparison_table = gr.Markdown(create_comparison_table(xy_pairs), height='300px')

    update_btn = gr.Button("Update")

    def update_table():
        for n in range(100):
            new_xy_pairs = []
            for i, (x, y) in enumerate(xy_pairs):
                new_xy_pairs.append((x, y, y[:n]))
            yield create_comparison_table(new_xy_pairs)
            time.sleep(0.02)

    update_btn.click(update_table, outputs=[comparison_table])



if __name__ == "__main__":
    demo.launch()
