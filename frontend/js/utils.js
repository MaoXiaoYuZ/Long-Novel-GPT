// 自动调整文本框大小
export function autoResizeTextarea(textarea) {
    // 保存滚动位置
    const container = document.getElementById('chunkContainer');
    const scrollTop = container.scrollTop;
    const windowScrollTop = window.scrollY || document.documentElement.scrollTop;
    
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px';
    
    // 恢复滚动位置
    container.scrollTop = scrollTop;
    window.scrollTo(0, windowScrollTop);
}

// 创建新的chunk
export function createNewChunk(x, y, revision, showRevision = false) {
    const chunkDiv = document.createElement('div');
    chunkDiv.className = 'chunk-container';
    
    chunkDiv.innerHTML = `
        <div class="x-item">
            <textarea class="x-input" placeholder="在这里输入...">${x}</textarea>
            <div class="chunk-actions">
                <button class="add-x-btn">+</button>
                <button class="delete-x-btn">-</button>
            </div>
        </div>
        <div class="y-item">
            <textarea class="y-input" placeholder="创作的内容会显示在这里...">${y}</textarea>
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
        
        extraChunks.forEach(newChunk => {
            const chunkDiv = createNewChunk(newChunk[0], newChunk[1], '', true);
            lastSelectedChunk.parentNode.insertBefore(chunkDiv, lastSelectedChunk.nextSibling);
            selectedChunks.push(chunkDiv);
            lastSelectedChunk = chunkDiv;
        });
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
    handleChunksAdjustment(data_chunks, selectedChunks);

    // 保存滚动位置
    const container = document.getElementById('chunkContainer');
    const scrollTop = container.scrollTop;
    const windowScrollTop = window.scrollY || document.documentElement.scrollTop;
    
    Array.from(selectedChunks).forEach((chunk, index) => {
        const newChunk = data_chunks[index];
        
        const revisionInput = chunk.querySelector('.revision-input');
        const revisionItem = chunk.querySelector('.revision-item');
        if (newChunk[2] == null) {  // 如果revision为null或undefined，则隐藏
            revisionItem.classList.remove('visible');
        } else {
            revisionItem.classList.add('visible');
            revisionInput.value = newChunk[2];
            autoResizeTextarea(revisionInput);
            if (showRevisionBtn) {
                // 显示接受/拒绝按钮
                const revisionActions = chunk.querySelector('.revision-actions');
                revisionActions.classList.remove('hidden');
            }
        }
        
        
        const xInput = chunk.querySelector('.x-input');
        const yInput = chunk.querySelector('.y-input');
        
        xInput.value = newChunk[0];
        autoResizeTextarea(xInput);
        yInput.value = newChunk[1];
        autoResizeTextarea(yInput);
        
    });
    
    // 恢复滚动位置
    container.scrollTop = scrollTop;
    window.scrollTo(0, windowScrollTop);
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