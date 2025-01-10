// 自动调整文本框大小
export function autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px';
}

// Function to stop a stream
export async function stopStream(streamId) {
    if (streamId) {
        try {
            await fetch(`${window._env_?.SERVER_URL}/stop_stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    stream_id: streamId
                })
            });
        } catch (error) {
            console.error('Error stopping stream:', error);
        }
    }
}

// 创建新的chunk
export function createNewChunk(x, y, revision, showRevision = false, showX = true, showY = true) {
    const chunkDiv = document.createElement('div');
    chunkDiv.className = 'chunk-container';
    
    chunkDiv.innerHTML = `
        <div class="x-item ${showX ? '' : 'hidden'}">
            <textarea class="x-input" placeholder="在这里输入...">${x}</textarea>
        </div>
        <div class="y-item ${showY ? '' : 'hidden'}">
            <textarea class="y-input" placeholder="创作的内容会显示在这里...">${y}</textarea>
            <div class="chunk-actions">
                <button class="add-x-btn">+</button>
                <button class="delete-x-btn">-</button>
            </div>
        </div>
        <div class="revision-item ${showRevision ? 'visible' : ''}">
            <textarea class="revision-input" placeholder="这里会显示修改稿...">${revision}</textarea>
            <div class="revision-actions hidden">
                <button class="accept-btn">接受</button>
                <button class="reject-btn">拒绝</button>
            </div>
        </div>
    `;
    
    return chunkDiv;
}

// 处理chunks的调整
function handleChunksAdjustment(data_chunks, selectedChunks) {
    if (data_chunks.length === selectedChunks.length) {
        return;
    }

    const selectedChunksArray = Array.from(selectedChunks);
    const newChunksCount = data_chunks.length;
    const selectedCount = selectedChunksArray.length;
    
    if (newChunksCount > selectedCount) {
        // 需添加新的chunks
        let lastSelectedChunk = selectedChunksArray[selectedCount - 1];
        const extraChunks = data_chunks.slice(selectedCount);
        
        // 获取最后一个chunk的x-item显示状态
        const showX = !lastSelectedChunk.querySelector('.x-item').classList.contains('hidden');
        
        // 使用DocumentFragment批量处理DOM操作
        const fragment = document.createDocumentFragment();
        const newSelectedChunks = [];
        
        extraChunks.forEach(newChunk => {
            const chunkDiv = createNewChunk(newChunk[0], newChunk[1], '', true, showX);
            fragment.appendChild(chunkDiv);
            newSelectedChunks.push(chunkDiv);
        });
        
        lastSelectedChunk.parentNode.insertBefore(fragment, lastSelectedChunk.nextSibling);
        selectedChunks.push(...newSelectedChunks);
    } else if (newChunksCount < selectedCount) {
        // 需要移除多余的chunks
        for (let i = newChunksCount; i < selectedCount; i++) {
            const chunkToRemove = selectedChunksArray[i];
            selectedChunks.splice(selectedChunks.indexOf(chunkToRemove), 1);
            chunkToRemove.remove();
        }
    }
}

// 更新chunks的内容
export function updateChunksContent(data_chunks, selectedChunks, showRevisionBtn) {
    // 保存滚动位置
    const container = document.getElementById('chunkContainer');
    const scrollTop = container.scrollTop;
    const windowScrollTop = window.scrollY || document.documentElement.scrollTop;
    
    handleChunksAdjustment(data_chunks, selectedChunks);
    
    // 收集所有需要调整大小的textareas
    const textareasToResize = [];
    
    Array.from(selectedChunks).forEach((chunk, index) => {
        const newChunk = data_chunks[index];
        
        const revisionInput = chunk.querySelector('.revision-input');
        const revisionItem = chunk.querySelector('.revision-item');
        if (newChunk[2] == null) {  // 如果revision为null或undefined，则隐藏
            revisionItem.classList.remove('visible');
        } else {
            revisionItem.classList.add('visible');
            revisionInput.value = newChunk[2];
            textareasToResize.push(revisionInput);
            if (showRevisionBtn) {
                // 显示接受/拒绝按钮
                const revisionActions = chunk.querySelector('.revision-actions');
                revisionActions.classList.remove('hidden');
            }
        }
        
        const xInput = chunk.querySelector('.x-input');
        const yInput = chunk.querySelector('.y-input');
        
        xInput.value = newChunk[0];
        yInput.value = newChunk[1];
        textareasToResize.push(xInput, yInput);
    });
    
    // 批量处理所有textarea的大小调整
    requestAnimationFrame(() => {
        textareasToResize.forEach(textarea => {
            textarea.style.height = 'auto';
            textarea.style.height = textarea.scrollHeight + 'px';
        });
        
        // 恢复滚动位置
        container.scrollTop = scrollTop;
        window.scrollTo(0, windowScrollTop);
    });
}

// Toast message function
export function showToast(message, type = 'info', duration = 3000) {
    // 确保container存在
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    // 创建toast元素
    const toast = document.createElement('div');
    toast.className = `toast-message ${type}`;
    
    // 添加图标
    const icon = document.createElement('span');
    icon.className = 'toast-icon';
    switch (type) {
        case 'success':
            icon.textContent = '✓';
            break;
        case 'error':
            icon.textContent = '✕';
            break;
        case 'warning':
            icon.textContent = '!';
            break;
        default:
            icon.textContent = 'ℹ';
    }
    
    // 添加消息文本
    const text = document.createElement('span');
    text.textContent = message;
    
    toast.appendChild(icon);
    toast.appendChild(text);
    container.appendChild(toast);

    // 显示动画
    requestAnimationFrame(() => {
        toast.classList.add('show');
    });

    // 自动移除
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            container.removeChild(toast);
            // 如果没有更多toast，移除container
            if (container.children.length === 0) {
                document.body.removeChild(container);
            }
        }, 300); // 等待淡出动画完成
    }, duration);
}

// 添加新的函数来控制左侧面板的显示/隐藏
export function toggleLeftPanel(show) {
    const contentSection = document.querySelector('.content-section');
    const leftPanel = contentSection.querySelector('.left-panel');
    const contentArea = contentSection.querySelector('.content-area');
    
    if (show) {
        // 显示左侧面板
        contentSection.classList.add('show-left-panel');
        const allXItems = document.querySelectorAll('.x-item');
        allXItems.forEach(item => item.classList.add('hidden'));
        
        if (!leftPanel) {
            const panel = document.createElement('div');
            panel.className = 'left-panel';
            panel.innerHTML = `
                <textarea class="left-panel-input" placeholder="在这里输入..."></textarea>
            `;
            
            // 如果content-area不存在，创建它
            if (!contentArea) {
                const area = document.createElement('div');
                area.className = 'content-area';
                area.appendChild(panel);
                area.appendChild(document.getElementById('chunkContainer'));
                
                // 将content-area插入到column-headers后面
                const headers = contentSection.querySelector('.column-headers');
                headers.after(area);
            } else {
                contentArea.insertBefore(panel, contentArea.firstChild);
            }
        }
    } else {
        // 隐藏左侧面板
        contentSection.classList.remove('show-left-panel');
        const allXItems = document.querySelectorAll('.x-item');
        allXItems.forEach(item => item.classList.remove('hidden'));
        if (leftPanel) {
            leftPanel.remove();
        }
    }
} 

// Modify storage keys based on mode and chapter
export function getStorageKey(mode, chapter = null) {
    if (mode === 'outline') {
        return `data_${mode}`;
    }
    return `data_${mode}_${chapter}`;
}

// Consolidated storage functions
export function saveDataToStorage(mode, chapter, chunks, context) {
    const key = getStorageKey(mode, chapter);
    const data = {
        chunks: chunks,
        context: context
    };
    
    try {
        localStorage.setItem(key, JSON.stringify(data));
        // console.log(`Saved ${mode} data to localStorage`);
        showToast('数据已保存', 'success', 1000);
    } catch (e) {
        console.error('Error saving to localStorage:', e);
        if (e.name === 'QuotaExceededError') {
            showToast('存储空间已满，请导出数据后清理存储空间', 'error');
        } else {
            showToast('保存失败', 'error');
        }
    }
}

export function getDataFromStorage(mode, chapter = null) {
    const key = getStorageKey(mode, chapter);
    try {
        const value = localStorage.getItem(key);
        if (!value) return { chunks: [], context: '' };
        return JSON.parse(value);
    } catch (e) {
        console.error('Error getting data from localStorage:', e);
        return { chunks: [], context: '' };
    }
}

// Bottom bar display functions
export function showBottomBar(content) {
    let bar = document.querySelector('.bottom-bar');
    if (!bar) {
        bar = document.createElement('div');
        bar.className = 'bottom-bar';
        document.body.appendChild(bar);
    }

    bar.innerHTML = `<span class="bottom-bar-content">${content}</span>`;
    
    // Ensure the bar is visible
    requestAnimationFrame(() => {
        bar.classList.add('visible');
    });
}

export function hideBottomBar() {
    const bar = document.querySelector('.bottom-bar');
    if (bar) {
        bar.classList.remove('visible');
        // Remove element after transition
        setTimeout(() => {
            if (bar.parentNode) {
                bar.parentNode.removeChild(bar);
            }
        }, 300);
    }
}

// Helper function to format cost display text
export function formatCostDisplay(modelName, cost, currencySymbol) {
    return `${modelName} (预计花费：${cost.toFixed(4)}${currencySymbol})`;
}