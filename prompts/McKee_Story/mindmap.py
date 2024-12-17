import matplotlib.pyplot as plt
import networkx as nx
import matplotlib.patheffects as pe
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np
import re

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Songti SC'] 
plt.rcParams['axes.unicode_minus'] = False

def wrap_text(text, max_width=15):
    """文本自动换行，优化中文处理"""
    if not text:
        return ""
    
    # 将文本按标点符号分割
    segments = re.split('([，。、；：\n])', text)
    lines = []
    current_line = ""
    
    for i in range(0, len(segments), 2):
        segment = segments[i]
        punct = segments[i + 1] if i + 1 < len(segments) else ""
        
        if len(current_line + segment + punct) <= max_width:
            current_line += segment + punct
        else:
            if current_line:
                lines.append(current_line)
            current_line = segment + punct
    
    if current_line:
        lines.append(current_line)
    
    return '\n'.join(lines)

def get_node_shape(role_type, gender):
    """根据角色类型和性别返回节点形状"""
    shapes = {
        ("protagonist", "male"): "o",      # 男主角用圆形
        ("protagonist", "female"): "h",    # 女主角用六边形
        ("supporting", "male"): "s",       # 男配角用方形
        ("supporting", "female"): "^",     # 女配角用三角形
        ("antagonist", "male"): "d",       # 男反派用钻石形
        ("antagonist", "female"): "v"      # 女反派用倒三角
    }
    return shapes.get((role_type, gender), "o")

def get_node_color(alignment):
    """根据角色立场返回颜色"""
    colors = {
        "good": "#3498DB",     # 更鲜明的蓝色
        "neutral": "#95A5A6",  # 更深的灰色
        "evil": "#E74C3C"      # 更鲜明的红色
    }
    return colors.get(alignment, "#95A5A6")

def get_relationship_style(relationship_type):
    """根据关系类型返回线条样式"""
    styles = {
        "mentor": {"style": "solid", "width_factor": 2.5},
        "friend": {"style": "solid", "width_factor": 2.0},
        "family": {"style": "solid", "width_factor": 2.5},
        "colleague": {"style": "dashed", "width_factor": 1.5},
        "antagonist": {"style": "dotted", "width_factor": 1.5},
        "student": {"style": "dashdot", "width_factor": 1.2}  # 添加学生关系类型
    }
    return styles.get(relationship_type, {"style": "solid", "width_factor": 1.0})

def prepare_nodes(characters, style_config):
    nodes = {}
    min_imp, max_imp = style_config["importance_scale"]
    imps = [c.get("importance", 1) for c in characters]
    if not imps:
        imps = [1]
    min_val, max_val = min(imps), max(imps)

    for char in characters:
        name = char["name"]
        gender = char.get("gender", "male")
        role_type = char.get("role_type", "supporting")
        alignment = char.get("alignment", "neutral")
        imp = char.get("importance", 1)

        shape = get_node_shape(role_type, gender)
        color = get_node_color(alignment)

        if max_val == min_val:
            size = (min_imp + max_imp) / 2
        else:
            normalized = (imp - min_val) / (max_val - min_val)
            size = min_imp + normalized * (max_imp - min_imp)

        inner_outer_conflict = char.get("inner_outer_conflict", "")
        personality = char.get("personality", "")

        nodes[name] = {
            "color": color,
            "shape": shape,
            "size": size,
            "data": char,
            "inner_outer_conflict": inner_outer_conflict,
            "personality": personality
        }

    return nodes

def get_edge_color(closeness):
    """根据亲密度返回边的颜色"""
    if closeness >= 0.7:
        return "#27AE60"  # 更深的绿色
    elif closeness >= 0.4:
        return "#F1C40F"  # 更鲜明的黄色
    else:
        return "#C0392B"  # 更深的红色

def prepare_edges(relationships):
    edges = []
    for rel in relationships:
        src = rel["source"]
        tgt = rel["target"]
        closeness = rel.get("closeness", 0.5)
        rel_type = rel.get("relationship_type", "normal")
        
        edge_color = get_edge_color(closeness)
        style = get_relationship_style(rel_type)
        width = style["width_factor"] * (1 + closeness)

        explanation = rel.get("explanation", "")
        explanation = wrap_text(explanation, max_width=6)

        edges.append((src, tgt, {
            "color": edge_color,
            "width": width,
            "style": style["style"],
            "data": rel,
            "explanation": explanation
        }))

    return edges

def draw_curved_edge(pos, node1, node2, color, width, style, ax):
    """绘制曲线边"""
    x1, y1 = pos[node1]
    x2, y2 = pos[node2]
    
    # 计算控制点
    mid_x = (x1 + x2) / 2
    mid_y = (y1 + y2) / 2
    
    # 添加一些随机偏移，使曲线更自然
    offset = 0.15
    control_x = mid_x + np.random.uniform(-offset, offset)
    control_y = mid_y + np.random.uniform(-offset, offset)
    
    # 创建贝塞尔曲线的点
    t = np.linspace(0, 1, 100)
    x = (1-t)**2 * x1 + 2*(1-t)*t * control_x + t**2 * x2
    y = (1-t)**2 * y1 + 2*(1-t)*t * control_y + t**2 * y2
    
    # 绘制曲线
    line = ax.plot(x, y, color=color, linewidth=width, 
                  linestyle=style, alpha=0.7, zorder=1)
    
    # 添加箭头
    arrow_pos = 0.6  # 箭头位置（0-1之间）
    arrow_idx = int(len(x) * arrow_pos)
    dx = x[arrow_idx+1] - x[arrow_idx-1]
    dy = y[arrow_idx+1] - y[arrow_idx-1]
    arrow = ax.arrow(x[arrow_idx], y[arrow_idx], dx*0.1, dy*0.1,
                    head_width=0.03, head_length=0.05, fc=color, ec=color,
                    alpha=0.7, zorder=2)
    
    return line, arrow

def create_fancy_bbox(x, y, text, facecolor, edgecolor, alpha=0.9, fontsize=10):
    """创建美化的文本框"""
    bbox_props = dict(
        boxstyle="round,pad=0.5,rounding_size=0.2",
        facecolor=facecolor,
        edgecolor=edgecolor,
        alpha=alpha,
        linewidth=0.8,
        mutation_aspect=0.3  # 控制文本框的宽高比
    )
    
    return plt.text(x, y, text,
                   color='#2C3E50',  # 更深的文字颜色
                   fontsize=fontsize,
                   ha='center', va='center',
                   bbox=bbox_props,
                   zorder=3)

def draw_conflict_connection(ax, start_x, start_y, end_x, end_y, color='#E74C3C'):
    """绘制内外矛盾连接线"""
    # 使用贝塞尔曲线创建优美的连接
    control_x = start_x
    control_y = end_y + 0.1
    
    t = np.linspace(0, 1, 50)
    x = (1-t)**2 * start_x + 2*(1-t)*t * control_x + t**2 * end_x
    y = (1-t)**2 * start_y + 2*(1-t)*t * control_y + t**2 * end_y
    
    # 绘制曲线
    line = ax.plot(x, y, color=color, linewidth=1, 
                  linestyle='--', alpha=0.4, zorder=1)
    
    return line

def create_fancy_conflict_box(x, y, text, ax):
    """创建更美观的内外矛盾文本框"""
    # 计算文本框大小
    bbox_props = dict(
        boxstyle="round,pad=0.5,rounding_size=0.2",
        facecolor='#FEF9E7',  # 淡黄色背景
        edgecolor='#F39C12',  # 橙色边框
        alpha=0.9,
        linewidth=1,
        mutation_aspect=0.3
    )
    
    # 添加小图标
    icon = '⚡'  # 使用闪电符号表示冲突
    
    text = f"{icon} {text}"
    
    return plt.text(x, y, text,
                   color='#2C3E50',
                   fontsize=9,
                   ha='center', va='center',
                   bbox=bbox_props,
                   zorder=4)

def custom_layout(G, k=2, iterations=50, scale=2):
    """自定义布局算法，增加节点间斥力和智能分布"""
    # 初始使用spring_layout获得基础布局
    pos = nx.spring_layout(G, k=k, iterations=iterations, scale=scale)
    
    # 迭代优化布局
    for _ in range(20):  # 额外的优化迭代
        # 计算节点间斥力
        for n1 in G.nodes():
            for n2 in G.nodes():
                if n1 != n2:
                    x1, y1 = pos[n1]
                    x2, y2 = pos[n2]
                    dx = x1 - x2
                    dy = y1 - y2
                    dist = np.sqrt(dx*dx + dy*dy)
                    
                    if dist < 0.5:  # 如果节点太近
                        # 计算斥力
                        force = 0.1 * (0.5 - dist)
                        angle = np.arctan2(dy, dx)
                        
                        # 应用斥力
                        pos[n1] = (x1 + force * np.cos(angle),
                                 y1 + force * np.sin(angle))
                        pos[n2] = (x2 - force * np.cos(angle),
                                 y2 - force * np.sin(angle))
    
    # 确保主角色（重要性高的）在中心位置
    center_node = max(G.nodes(), key=lambda n: G.nodes[n].get('size', 0))
    center_pos = pos[center_node]
    
    # 调整所有节点位置，使主角色位于中心
    center_x = np.mean([p[0] for p in pos.values()])
    center_y = np.mean([p[1] for p in pos.values()])
    offset_x = 0 - center_x
    offset_y = 0 - center_y
    
    for node in pos:
        x, y = pos[node]
        pos[node] = (x + offset_x, y + offset_y)
    
    return pos

def calculate_conflict_position(x, y, center_x, center_y, offset=0.6):
    """计算内外矛盾的位置，基于节点相对于中心点的位置"""
    dx = x - center_x
    dy = y - center_y
    dist = np.sqrt(dx*dx + dy*dy)
    
    if dist < 0.1:  # 如果节点非常接近中心
        return x, y + offset  # 默认放在上方
    
    # 归一化方向向量
    if dist > 0:
        dx = dx / dist
        dy = dy / dist
    
    # 计算偏移位置
    conflict_x = x + dx * offset
    conflict_y = y + dy * offset
    
    return conflict_x, conflict_y

def draw_network(nodes, edges):
    G = nx.Graph()
    for n, attr in nodes.items():
        G.add_node(n, **attr)
    for src, tgt, attr in edges:
        G.add_edge(src, tgt, **attr)

    # 设置图形大小和背景
    plt.figure(figsize=(20, 15))
    fig = plt.gcf()
    fig.set_facecolor('#ffffff')
    ax = plt.gca()
    ax.set_facecolor('#ffffff')

    # 使用自定义布局
    pos = custom_layout(G, k=3, iterations=100, scale=3)

    # 计算中心点
    center_x = np.mean([p[0] for p in pos.values()])
    center_y = np.mean([p[1] for p in pos.values()])

    # 绘制边（最底层）
    for (u, v, d) in G.edges(data=True):
        draw_curved_edge(pos, u, v, d["color"], d["width"], d["style"], ax)

    # 绘制边标签
    edge_labels = {}
    for u, v, d in G.edges(data=True):
        explanation = d.get("explanation", "")
        if explanation:
            x1, y1 = pos[u]
            x2, y2 = pos[v]
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2
            
            # 增加偏移以避免重叠
            offset = 0.15
            angle = np.arctan2(y2 - y1, x2 - x1)
            mid_x += offset * np.cos(angle + np.pi/2)
            mid_y += offset * np.sin(angle + np.pi/2)
            
            create_fancy_bbox(mid_x, mid_y,
                            wrap_text(explanation, max_width=15),
                            'white',
                            '#BDC3C7',
                            fontsize=9)

    # 显示内在冲突标签
    conflict_boxes = {}
    for n, data in G.nodes(data=True):
        conflict = data["inner_outer_conflict"]
        if conflict:
            x, y = pos[n]
            # 计算内外矛盾的位置
            conflict_x, conflict_y = calculate_conflict_position(x, y, center_x, center_y, offset=0.8)
            
            # 创建内外矛盾文本框
            conflict_box = create_fancy_conflict_box(conflict_x, conflict_y,
                                                   wrap_text(conflict, max_width=20),
                                                   ax)
            conflict_boxes[n] = (conflict_x, conflict_y)
            
            # 计算连接线的控制点
            control_x = x + (conflict_x - x) * 0.3
            control_y = y + (conflict_y - y) * 0.3
            
            # 绘制优化的连接线
            t = np.linspace(0, 1, 50)
            curve_x = (1-t)**2 * x + 2*(1-t)*t * control_x + t**2 * conflict_x
            curve_y = (1-t)**2 * y + 2*(1-t)*t * control_y + t**2 * conflict_y
            ax.plot(curve_x, curve_y, color='#E74C3C', linewidth=1, 
                   linestyle='--', alpha=0.4, zorder=1)

    # 显示性格标签
    for n, data in G.nodes(data=True):
        personality = data["personality"]
        if personality:
            x, y = pos[n]
            # 计算性格标签的位置（总是在下方）
            offset_y = 0.3
            create_fancy_bbox(x, y - offset_y,
                            wrap_text(personality, max_width=15),
                            '#EBF5FB',
                            '#AED6F1',
                            fontsize=9)

    # 绘制节点（最上层）
    for n, data in G.nodes(data=True):
        nx.draw_networkx_nodes(
            G, pos,
            nodelist=[n],
            node_color=data["color"],
            node_shape=data["shape"],
            node_size=data["size"],
            alpha=0.9,
            edgecolors='#2C3E50',
            linewidths=2.0
        )

    # 绘制节点名称标签
    for n, data in G.nodes(data=True):
        x, y = pos[n]
        text_obj = plt.text(x, y,
                          s=n,
                          color='#2C3E50',
                          fontsize=13,
                          fontweight='bold',
                          ha='center', va='center',
                          bbox=dict(facecolor='white',
                                  alpha=0.8,
                                  edgecolor='none',
                                  pad=1))
        text_obj.set_path_effects([
            pe.withStroke(linewidth=3, foreground='white'),
            pe.Normal()
        ])

    # 添加图例
    legend_elements = [
        mpatches.Patch(color="#3498DB", label='正面角色'),
        mpatches.Patch(color="#95A5A6", label='中立角色'),
        mpatches.Patch(color="#E74C3C", label='反面角色'),
        mpatches.Patch(color="#27AE60", label='密切关系'),
        mpatches.Patch(color="#F1C40F", label='一般关系'),
        mpatches.Patch(color="#C0392B", label='紧张关系')
    ]
    
    plt.legend(handles=legend_elements,
              loc='upper left',
              bbox_to_anchor=(1.05, 1),
              fontsize=10,
              title='图例',
              title_fontsize=12)

    plt.axis('off')
    plt.title("《生活的转折点》角色关系图",
              fontweight='bold',
              fontsize=18,
              pad=20,
              color='#2C3E50')
    
    # 增加边距以显示完整的内外矛盾标签
    plt.margins(x=0.25, y=0.25)
    
    plt.tight_layout()
    plt.savefig("relationship_chart_enhanced.png",
                dpi=300,
                bbox_inches='tight',
                facecolor='white',
                edgecolor='none')
    plt.show()

def process_character_data(json_data):
    """处理角色数据JSON"""
    characters = []
    i = 1
    while True:
        name_key = f"name_{i}"
        if name_key not in json_data or not json_data[name_key]:
            break
            
        character = {
            "name": json_data[f"name_{i}"],
            "gender": json_data[f"gender_{i}"],
            "importance": json_data[f"importance_{i}"],
            "alignment": json_data[f"alignment_{i}"],
            "role_type": json_data[f"role_type_{i}"],
            "inner_outer_conflict": json_data[f"inner_outer_conflict_{i}"],
            "personality": json_data[f"personality_{i}"]
        }
        characters.append(character)
        i += 1
    return characters

def process_relationship_data(json_data):
    """处理关系数据JSON"""
    relationships = []
    i = 1
    while True:
        source_key = f"source_{i}"
        if source_key not in json_data or not json_data[source_key]:
            break
            
        relationship = {
            "source": json_data[f"source_{i}"],
            "target": json_data[f"target_{i}"],
            "closeness": json_data[f"closeness_{i}"],
            "relationship_type": json_data[f"relationship_type_{i}"],
            "explanation": json_data[f"explanation_{i}"]
        }
        relationships.append(relationship)
        i += 1
    return relationships

if __name__ == "__main__":
    import json
    
    # 读取角色数据
    with open('json_data/character_relationship_map_《生活的转折点》.json', 'r', encoding='utf-8') as f:
        character_data = json.load(f)
    characters = process_character_data(character_data)
    
    # 读取关系数据
    with open('json_data/relationship_map_《生活的转折点》.json', 'r', encoding='utf-8') as f:
        relationship_data = json.load(f)
    relationships = process_relationship_data(relationship_data)

    style_config = {
        "importance_scale": (800, 3000)  # 调整节点大小范围
    }

    node_attrs = prepare_nodes(characters, style_config)
    edge_attrs = prepare_edges(relationships)
    draw_network(node_attrs, edge_attrs)
