// 直接将数据嵌入到代码中
const characterData = {
    "name_1": "李明",
    "gender_1": "male",
    "importance_1": 5,
    "alignment_1": "good",
    "role_type_1": "protagonist",
    "inner_outer_conflict_1": "内在对教育理想的追求与外界对教师职业的轻视之间的矛盾",
    "personality_1": "内向、敏感、理性，渴望自我价值的实现",
    "name_2": "小张",
    "gender_2": "male",
    "importance_2": 4,
    "alignment_2": "good",
    "role_type_2": "supporting",
    "inner_outer_conflict_2": "努力保持乐观外表掩饰内心对职业的焦虑和对失败的恐惧",
    "personality_2": "积极向上、乐观、幽默，能够带动周围的气氛",
    "name_3": "校长",
    "gender_3": "male",
    "importance_3": 4,
    "alignment_3": "neutral",
    "role_type_3": "supporting",
    "inner_outer_conflict_3": "希望提升教育质量，但无法理解教师的实际困难",
    "personality_3": "严厉、冷静，有远见与决策能力",
    "name_4": "林老师",
    "gender_4": "female",
    "importance_4": 3,
    "alignment_4": "good",
    "role_type_4": "supporting",
    "inner_outer_conflict_4": "如何在教育改革中保持个人特色，面临上级的压力",
    "personality_4": "经验丰富、耐心、关怀学生",
    "name_5": "王家长",
    "gender_5": "male",
    "importance_5": 3,
    "alignment_5": "evil",
    "role_type_5": "antagonist",
    "inner_outer_conflict_5": "对孩子未来的期望与对教育体制的不满之间的冲突",
    "personality_5": "传统、强势，极为重视孩子的教育成果"
};

const relationshipData = {
    "source_1": "李明",
    "target_1": "小张",
    "closeness_1": 0.9,
    "relationship_type_1": "friend",
    "explanation_1": "他作为李明的支持者，互相理解与帮助，共同成长。",
    "source_2": "李明",
    "target_2": "校长",
    "closeness_2": 0.4,
    "relationship_type_2": "colleague",
    "explanation_2": "校长对李明的职业发展给予关注，但存在冲突和压力。",
    "source_3": "李明",
    "target_3": "林老师",
    "closeness_3": 0.7,
    "relationship_type_3": "colleague",
    "explanation_3": "林老师提供经验，帮助李明应对教学挑战。",
    "source_4": "李明",
    "target_4": "王家长",
    "closeness_4": 0.2,
    "relationship_type_4": "antagonist",
    "explanation_4": "王家长对李明的教学理念提出质疑，形成压力。"
};

// 直接调用创建图形函数
document.addEventListener('DOMContentLoaded', function() {
    createGraph(characterData, relationshipData);
});

function processCharacterData(data) {
    const characters = [];
    let i = 1;
    while (data[`name_${i}`]) {
        characters.push({
            id: data[`name_${i}`],
            name: data[`name_${i}`],
            gender: data[`gender_${i}`],
            importance: data[`importance_${i}`],
            alignment: data[`alignment_${i}`],
            roleType: data[`role_type_${i}`],
            innerOuterConflict: data[`inner_outer_conflict_${i}`],
            personality: data[`personality_${i}`]
        });
        i++;
    }
    return characters;
}

function processRelationshipData(data) {
    const relationships = [];
    let i = 1;
    while (data[`source_${i}`]) {
        relationships.push({
            source: data[`source_${i}`],
            target: data[`target_${i}`],
            closeness: data[`closeness_${i}`],
            relationshipType: data[`relationship_type_${i}`],
            explanation: data[`explanation_${i}`]
        });
        i++;
    }
    return relationships;
}

function getNodeColor(alignment) {
    const colors = {
        "good": "#3498DB",
        "neutral": "#95A5A6",
        "evil": "#E74C3C"
    };
    return colors[alignment] || "#95A5A6";
}

function getLinkColor(closeness) {
    if (closeness >= 0.7) return "#27AE60";
    if (closeness >= 0.4) return "#F1C40F";
    return "#C0392B";
}

function getNodeShape(roleType) {
    const shapes = {
        "protagonist": "circle",    // 主角用圆形
        "antagonist": "diamond",    // 反派用菱形
        "supporting": "rect",       // 配角用方形
        "mentor": "triangle-up",    // 导师用三角形
        "student": "triangle-down"  // 学生用倒三角
    };
    return shapes[roleType] || "circle";
}

function wrapText(text, width = 15) {
    if (!text) return [];
    const words = text.split('');
    const lines = [];
    let line = '';
    
    for (let word of words) {
        if (line.length + 1 > width) {
            lines.push(line);
            line = word;
        } else {
            line += word;
        }
    }
    if (line) {
        lines.push(line);
    }
    return lines;
}

function getRelationshipLabel(type) {
    const labels = {
        "friend": "朋友",
        "colleague": "同事",
        "mentor": "导师",
        "student": "学生",
        "antagonist": "对立",
        "family": "家人"
    };
    return labels[type] || type;
}

function createGraph(characterData, relationshipData) {
    const width = window.innerWidth - 40;
    const height = window.innerHeight - 40;
    
    const characters = processCharacterData(characterData);
    const relationships = processRelationshipData(relationshipData);
    
    // 创建SVG容器
    const svg = d3.select('.container')
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .style('background-color', 'transparent');
    
    // 添加模糊效果滤镜
    const defs = svg.append('defs');
    
    // 发光效果
    const glowFilter = defs.append('filter')
        .attr('id', 'glow')
        .attr('x', '-50%')
        .attr('y', '-50%')
        .attr('width', '200%')
        .attr('height', '200%');
    
    glowFilter.append('feGaussianBlur')
        .attr('stdDeviation', '3')
        .attr('result', 'coloredBlur');
    
    const glowMerge = glowFilter.append('feMerge');
    glowMerge.append('feMergeNode')
        .attr('in', 'coloredBlur');
    glowMerge.append('feMergeNode')
        .attr('in', 'SourceGraphic');
    
    // 创建力导向图
    const simulation = d3.forceSimulation(characters)
        .force('link', d3.forceLink(relationships).id(d => d.id).distance(400))
        .force('charge', d3.forceManyBody().strength(-5000))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(d => Math.sqrt(d.importance) * 80))
        .force('x', d3.forceX(width / 2).strength(0.1))
        .force('y', d3.forceY(height / 2).strength(0.1));
    
    // 创建箭头标记
    defs.selectAll('marker')
        .data(['end'])
        .join('marker')
        .attr('id', d => `arrow-${d}`)
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 25)
        .attr('refY', 0)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('fill', '#999')
        .attr('d', 'M0,-5L10,0L0,5');
    
    // 绘制连接线
    const links = svg.append('g')
        .selectAll('path')
        .data(relationships)
        .join('path')
        .attr('class', 'link connection-line')
        .attr('stroke', d => getLinkColor(d.closeness))
        .attr('stroke-width', d => 2 * d.closeness)
        .attr('fill', 'none')
        .style('filter', 'url(#glow)')
        .attr('marker-end', 'url(#arrow-end)');
    
    // 修改关系标签的创建
    const linkLabels = svg.append('g')
        .selectAll('g')
        .data(relationships)
        .join('g')
        .attr('class', 'link-label');
    
    // 创建标签组
    const labelGroups = linkLabels.append('g')
        .attr('class', 'label-group')
        .style('opacity', 1);
    
    // 添加关系类型标签
    labelGroups.append('text')
        .attr('class', 'link-label-text')
        .text(d => getRelationshipLabel(d.relationshipType))
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'middle')
        .attr('dy', -10);
    
    // 添加关系说明标签
    labelGroups.append('text')
        .attr('class', 'link-label-text explanation-text')
        .text(d => d.explanation || '')
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'middle')
        .attr('dy', 10)
        .each(function(d) {
            // 自动换行处理
            const text = d3.select(this);
            const words = (d.explanation || '').split('');
            const lineHeight = 16;
            const maxWidth = 120;
            let line = '';
            let lineNumber = 0;
            
            text.text(''); // 清空原有文本
            
            words.forEach((char, i) => {
                line += char;
                if (line.length >= 10 || i === words.length - 1) {
                    text.append('tspan')
                        .attr('x', 0)
                        .attr('dy', lineNumber === 0 ? 0 : lineHeight)
                        .text(line);
                    line = '';
                    lineNumber++;
                }
            });
        });
    
    // 为每个标签组添加背景框
    labelGroups.each(function() {
        const group = d3.select(this);
        const bbox = this.getBBox();
        const padding = 8;
        
        group.insert('rect', 'text')
            .attr('class', 'link-label-bg')
            .attr('x', bbox.x - padding)
            .attr('y', bbox.y - padding)
            .attr('width', bbox.width + 2*padding)
            .attr('height', bbox.height + 2*padding)
            .attr('rx', 6)
            .attr('ry', 6);
    });
    
    // 创建节点组
    const nodeGroups = svg.append('g')
        .selectAll('g')
        .data(characters)
        .join('g')
        .attr('class', 'node-group')
        .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended));
    
    // 添加节点闪光效果
    nodeGroups.append('circle')
        .attr('class', 'node-highlight')
        .attr('r', d => Math.sqrt(d.importance) * 20 + 4);
    
    // 绘制节点
    nodeGroups.each(function(d) {
        const node = d3.select(this);
        const shape = getNodeShape(d.roleType);
        
        switch(shape) {
            case 'circle':
                node.append('circle')
                    .attr('class', 'node')
                    .attr('r', d => Math.sqrt(d.importance) * 20)
                    .style('filter', 'url(#glow)');
                break;
            case 'rect':
                const size = Math.sqrt(d.importance) * 35;
                node.append('rect')
                    .attr('class', 'node')
                    .attr('width', size)
                    .attr('height', size)
                    .attr('x', -size/2)
                    .attr('y', -size/2)
                    .style('filter', 'url(#glow)');
                break;
            case 'diamond':
                const dsize = Math.sqrt(d.importance) * 35;
                node.append('path')
                    .attr('class', 'node')
                    .attr('d', d3.symbol().type(d3.symbolDiamond).size(dsize * 40));
                break;
            case 'triangle-up':
                const tsize = Math.sqrt(d.importance) * 35;
                node.append('path')
                    .attr('class', 'node')
                    .attr('d', d3.symbol().type(d3.symbolTriangle).size(tsize * 40));
                break;
            case 'triangle-down':
                const tdsize = Math.sqrt(d.importance) * 35;
                node.append('path')
                    .attr('class', 'node')
                    .attr('d', d3.symbol().type(d3.symbolTriangle).size(tdsize * 40))
                    .attr('transform', 'rotate(180)');
                break;
        }
        
        node.select('.node')
            .attr('fill', d => getNodeColor(d.alignment))
            .attr('stroke', '#2C3E50')
            .attr('stroke-width', 2);
    });
    
    // 添加节点标签
    nodeGroups.append('text')
        .attr('class', 'node-label')
        .text(d => d.name)
        .attr('dy', '0.35em');
    
    // 添加性格标签
    const personalityGroups = nodeGroups.append('g')
        .attr('class', 'personality-group')
        .attr('transform', 'translate(0, 40)');
    
    personalityGroups.each(function(d) {
        const group = d3.select(this);
        const lines = wrapText(d.personality);
        const boxHeight = lines.length * 16 + 10;
        
        group.append('rect')
            .attr('class', 'personality-box text-content')
            .attr('x', -80)
            .attr('y', -boxHeight/2)
            .attr('width', 160)
            .attr('height', boxHeight);
        
        lines.forEach((line, i) => {
            group.append('text')
                .attr('class', 'personality-text')
                .attr('x', 0)
                .attr('y', -boxHeight/2 + 16 + i * 16)
                .attr('text-anchor', 'middle')
                .text(line);
        });
    });
    
    // 添加内外矛盾标签
    const conflictGroups = nodeGroups.append('g')
        .attr('class', 'conflict-group')
        .attr('transform', 'translate(0, -60)');
    
    conflictGroups.each(function(d) {
        const group = d3.select(this);
        const lines = wrapText(d.innerOuterConflict);
        const boxHeight = lines.length * 16 + 10;
        
        group.append('rect')
            .attr('class', 'conflict-box text-content')
            .attr('x', -80)
            .attr('y', -boxHeight/2)
            .attr('width', 160)
            .attr('height', boxHeight);
        
        lines.forEach((line, i) => {
            group.append('text')
                .attr('class', 'conflict-text')
                .attr('x', 0)
                .attr('y', -boxHeight/2 + 16 + i * 16)
                .attr('text-anchor', 'middle')
                .text(line);
        });
    });
    
    // 添加交互效果
    nodeGroups.on('mouseover', function(event, d) {
        const node = d3.select(this);
        node.select('.node').classed('highlighted', true);
        
        // 高亮相关连接
        links.classed('dimmed', link => 
            link.source.id !== d.id && link.target.id !== d.id);
        
        // 高亮相关节点
        nodeGroups.classed('highlighted', node => {
            const isConnected = relationships.some(link => 
                (link.source.id === d.id && link.target.id === node.id) ||
                (link.target.id === d.id && link.source.id === node.id));
            return node.id === d.id || isConnected;
        });
        
        // 显示相关的标签
        linkLabels.selectAll('.label-group')
            .style('opacity', label => {
                const isRelated = label.source.id === d.id || label.target.id === d.id;
                return isRelated ? 1 : 0;
            })
            .style('transform', label => {
                const isRelated = label.source.id === d.id || label.target.id === d.id;
                return isRelated ? 'scale(1)' : 'scale(0.8)';
            });
    })
    .on('mouseout', function() {
        nodeGroups.select('.node').classed('highlighted', false);
        links.classed('dimmed', false);
        linkLabels.selectAll('.label-group')
            .style('opacity', 0)
            .style('transform', 'scale(0.8)');
    });
    
    // 修改tick事件处理
    simulation.on('tick', () => {
        // 限制节点位置在视图范围内
        characters.forEach(d => {
            d.x = Math.max(100, Math.min(width - 100, d.x));
            d.y = Math.max(100, Math.min(height - 100, d.y));
        });

        // 更新连接线
        links.attr('d', d => {
            const dx = d.target.x - d.source.x;
            const dy = d.target.y - d.source.y;
            const dr = Math.sqrt(dx * dx + dy * dy) * 1.5; // 增加曲线弧度
            return `M${d.source.x},${d.source.y}A${dr},${dr} 0 0,1 ${d.target.x},${d.target.y}`;
        });

        // 更新节点位置
        nodeGroups.attr('transform', d => `translate(${d.x},${d.y})`);

        // 更新标签位置
        linkLabels.attr('transform', d => {
            const dx = d.target.x - d.source.x;
            const dy = d.target.y - d.source.y;
            const angle = Math.atan2(dy, dx) * 180 / Math.PI;
            
            // 计算标签位置，使用二次贝塞尔曲线的中点
            const midX = (d.source.x + d.target.x) / 2;
            const midY = (d.source.y + d.target.y) / 2;
            
            // 添加垂直偏移，避免标签重叠
            const offset = 40;
            const perpX = -dy / Math.sqrt(dx * dx + dy * dy) * offset;
            const perpY = dx / Math.sqrt(dx * dx + dy * dy) * offset;

            return `translate(${midX + perpX},${midY + perpY})`;
        });
    });
    
    // 修改CSS动画方向
    svg.selectAll('.connection-line').style('stroke-dasharray', '5,5')
        .style('animation', 'dash 20s linear reverse infinite');
    
    // 添加缩放功能
    const zoom = d3.zoom()
        .scaleExtent([0.5, 2])
        .on('zoom', (event) => {
            svg.selectAll('g').attr('transform', event.transform);
        });
    
    svg.call(zoom);
    
    // 拖拽功能
    function dragstarted(event) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
    }
    
    function dragged(event) {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
    }
    
    function dragended(event) {
        if (!event.active) simulation.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
    }
} 