import { autoResizeTextarea, createNewChunk, updateChunksContent, showToast, stopStream, showBottomBar, hideBottomBar, formatCostDisplay } from './utils.js';

document.addEventListener('DOMContentLoaded', () => {
    const chunkContainer = document.getElementById('chunkContainer');
    const actionBtn = document.querySelector('.action-btn');
    let selectedChunks = [];
    let lastSelectedIndex = -1;
    let isWriting = false;
    let originalChunksData = null;
    let currentController = null;
    let currentStreamId = null;
    let currentMode = 'outline';

    function handleChunkSelection(e) {
        // 如果正在创作，则不允许选择
        if (isWriting) {
            return;
        }

        const chunk = e.target.closest('.chunk-container');
        if (!chunk || (!e.target.classList.contains('x-input') && !e.target.classList.contains('y-input'))) {
            return;
        }

        const allChunks = Array.from(document.querySelectorAll('.chunk-container'));
        const currentIndex = allChunks.indexOf(chunk);
        
        if (e.shiftKey && lastSelectedIndex !== -1) {
            // Shift键多选
            const start = Math.min(lastSelectedIndex, currentIndex);
            const end = Math.max(lastSelectedIndex, currentIndex);
            
            // 清除之前的选择
            selectedChunks = [];
            allChunks.forEach(c => c.classList.remove('selected'));
            
            // 选择范围内的所有chunk
            for (let i = start; i <= end; i++) {
                allChunks[i].classList.add('selected');
                selectedChunks.push(allChunks[i]);
            }
        } else if (e.ctrlKey || e.metaKey) {
            // Ctrl/Cmd键切换选择
            if (selectedChunks.includes(chunk)) {
                selectedChunks = selectedChunks.filter(c => c !== chunk);
                chunk.classList.remove('selected');
            } else {
                // 添加新chunk并按DOM顺序排序
                selectedChunks.push(chunk);
                selectedChunks.sort((a, b) => allChunks.indexOf(a) - allChunks.indexOf(b));
                chunk.classList.add('selected');
            }
            lastSelectedIndex = currentIndex;
        } else {
            // 普通点击，清除其他选择
            selectedChunks.forEach(c => c.classList.remove('selected'));
            selectedChunks = [chunk];
            chunk.classList.add('selected');
            lastSelectedIndex = currentIndex;
        }
    }

    // 在 showRevisionAreas 函数前添加这个新函数
    function handleBatchRevision(accept) {
        // 获取所有可见的revision items对应的chunks
        const visibleRevisions = document.querySelectorAll('.revision-item.visible');
        visibleRevisions.forEach(revisionItem => {
            const chunk = revisionItem.closest('.chunk-container');
            handleRevision(chunk, accept);
        });
    }

    // 更新按钮文本
    function updateActionButtonText() {
        actionBtn.textContent = isWriting ? '取消创作' : '开始创作';
    }

    // 添加新的函数来处理端请求
    async function requestAIWriting(allChunks, span, callbacks) {
        try {
            // 如果存在之前的controller，先中止它
            if (currentController) {
                currentController.abort();
                await stopStream(currentStreamId);
            }
            
            currentController = new AbortController();
            currentStreamId = null;
            
            // Get writer mode from the select element
            const writerMode = document.getElementById('writeMode').value;
            
            // Get prompt content from the textarea
            const promptContent = document.querySelector('.prompt-input textarea').value;

            const windowSizeStr = document.querySelector('.context-window-select').value;
            const { x: x_chunk_length, y: y_chunk_length } = JSON.parse(windowSizeStr);
            
            // Get selected model provider            
            const settings = JSON.parse(localStorage.getItem('settings'));
            
            const requestData = {
                writer_mode: writerMode,
                chunk_list: allChunks,
                chunk_span: span,
                prompt_content: promptContent,
                x_chunk_length: x_chunk_length,
                y_chunk_length: y_chunk_length,
                main_model: settings.MAIN_MODEL,
                sub_model: settings.SUB_MODEL,
                global_context: writerMode !== 'draft' ? document.querySelector('.left-panel-input').value : '',
                settings: {
                    MAX_THREAD_NUM: settings.MAX_THREAD_NUM,
                }
            };
            
            const response = await fetch(`${window._env_?.SERVER_URL}/write`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData),
                signal: currentController.signal
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let prevChunks = null;

            while (true) {
                try {
                    const {value, done} = await reader.read();
                    if (done) break;
                    
                    buffer += decoder.decode(value, {stream: true});
                    const lines = buffer.split('\n');
                    
                    while (lines.length > 1) {
                        const line = lines.shift();
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                
                                // Store stream ID if received
                                if (data.stream_id) {
                                    currentStreamId = data.stream_id;
                                    continue;
                                }
                                
                                // 处理delta更新
                                if (data.chunk_type === 'delta' && prevChunks) {
                                    const updatedChunks = data.chunk_list.map((chunk, i) => {
                                        return chunk.map((str, j) => prevChunks[i][j] + str);
                                    });
                                    data.chunk_list = updatedChunks;
                                }
                                prevChunks = data.chunk_list;
                                callbacks.onData(data);
                            } catch (e) {
                                console.error('Error parsing SSE data:', e);
                            }
                        }
                    }
                    buffer = lines[0] || '';
                } catch (error) {
                    if (error.name === 'AbortError') {
                        await stopStream(currentStreamId);
                        throw error;
                    }
                    console.error('Stream processing error:', error);
                    throw error;
                }
            }
        } finally {
            currentController = null;
            currentStreamId = null;
        }
    }

    // 创作的处理函数
    async function handleCreateAction() {
        if (isWriting) {
            // 取消创作
            isWriting = false;
            updateActionButtonText();
            
            // 中止当前的请求
            if (currentController) {
                currentController.abort();
            }
            
            // 恢复原始状态
            if (!originalChunksData) {
                console.error('originalChunksData should not be null when canceling creation');
                return;
            }
            updateChunksContent(originalChunksData, selectedChunks, false);
            selectedChunks.forEach(chunk => chunk.classList.add('selected'));
            
            // 隐藏批量操作按钮
            const batchActions = document.querySelector('.batch-actions');
            if (batchActions) {
                batchActions.classList.add('hidden');
            }

            hideBottomBar();
            
            originalChunksData = null;
            return;
        }

        // 验证选择的chunks
        if (selectedChunks.length === 0) {
            // 自动选择所有chunks
            const allChunks = Array.from(document.querySelectorAll('.chunk-container'));
            selectedChunks = allChunks;
            allChunks.forEach(chunk => chunk.classList.add('selected'));
            lastSelectedIndex = allChunks.length - 1;
            
            showToast('已自动选择所有内容', 'info');     
            // showToast('请先选择要创作的内容', 'warning');
        }

        // 验证chunks连续性
        const allChunks = Array.from(document.querySelectorAll('.chunk-container'));
        const firstIndex = allChunks.indexOf(selectedChunks[0]);
        const lastIndex = allChunks.indexOf(selectedChunks[selectedChunks.length - 1]); 
        const isContinuous = lastIndex - firstIndex + 1 === selectedChunks.length;
        if (!isContinuous) {
            showToast('请选择连续的文本', 'warning');
            return;
        }

        // 开始创作流程
        isWriting = true;
        originalChunksData = selectedChunks.map(chunk => [
            chunk.querySelector('.x-input').value,
            chunk.querySelector('.y-input').value,      // revision设为undefined
        ]);
        updateActionButtonText();
        //showRevisionAreas(selectedChunks);

        const selectedChunksData = selectedChunks.map(chunk => [
            chunk.querySelector('.x-input').value,
            chunk.querySelector('.y-input').value,
            '正在生成...'
        ]);
        updateChunksContent(selectedChunksData, selectedChunks, false);

        selectedChunks.forEach(chunk => chunk.querySelector('.revision-actions').classList.add('hidden'));

        try {
            // 准备请求数据
            const chunksData = allChunks.map(chunk => [
                chunk.querySelector('.x-input').value,
                chunk.querySelector('.y-input').value
            ]);
            const selectedIndices = selectedChunks.map(chunk => allChunks.indexOf(chunk));
            const span = [Math.min(...selectedIndices), Math.max(...selectedIndices) + 1];
            if (span[0] < 0 || span[1] < 0) throw new Error('span不合法');
            await requestAIWriting(chunksData, span, {
                onData: (data) => {
                    updateChunksContent(data.chunk_list, selectedChunks, data.done);
                    selectedChunks.forEach(chunk => chunk.classList.add('selected'));
                    
                    // 更新cost display
                    if (data.msg) {
                        showBottomBar(data.msg);
                    }
                    
                    // 当生成完成时显示批量操作按钮
                    if (data.done) {
                        selectedChunks.forEach(chunk => chunk.querySelector('.revision-actions').classList.remove('hidden'));

                        const batchActions = document.querySelector('.batch-actions');
                        if (batchActions) {
                            batchActions.classList.remove('hidden');
                        }
                    }
                }
            });
        } catch (error) {
            if (error.name === 'AbortError') {
                console.log('Writing was canceled');
                hideBottomBar();
                return;
            }
            console.error('Writing Error:', error);
            selectedChunks.forEach(chunk => {
                const revisionInput = chunk.querySelector('.revision-input');
                revisionInput.value = `生成出错：${error.message}`;
                autoResizeTextarea(revisionInput);
            });
            hideBottomBar();
        }
    }

    function handleRevision(chunk, accept) {
        chunk.querySelector('.revision-item').classList.remove('visible');

        const pendingRevisions = document.querySelectorAll('.revision-item.visible');
        if (pendingRevisions.length === 0) {
            isWriting = false;
            updateActionButtonText();
            originalChunksData = null;
            selectedChunks.forEach(c => c.classList.remove('selected'));
            selectedChunks = [];
            
            // Hide cost display when done
            hideBottomBar();
            
            // 隐藏批量操作按钮
            const batchActions = document.querySelector('.batch-actions');
            if (batchActions) {
                batchActions.classList.add('hidden');
            }
        }

        if (accept) {
            const yInput = chunk.querySelector('.y-input');
            const revisionInput = chunk.querySelector('.revision-input');
            yInput.value = revisionInput.value;
            autoResizeTextarea(yInput);
        } else {
            // 在拒绝时检查x和y输入是否都为空
            const xInput = chunk.querySelector('.x-input');
            const yInput = chunk.querySelector('.y-input');
            if (!xInput.value.trim() && !yInput.value.trim()) {
                // 找到删除按钮并触发点击事件
                const deleteBtn = chunk.querySelector('.delete-x-btn');
                deleteBtn.click();
            }
        }
    }

    function initializeEventListeners() {
        // 监听所有文本框的输入事件，自动调整高度
        document.addEventListener('input', (e) => {
            if (e.target.classList.contains('x-input') || 
                e.target.classList.contains('y-input') || 
                e.target.classList.contains('revision-input')) {
                autoResizeTextarea(e.target);
            }
        });

        // 监听添加按钮的点击
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('add-x-btn')) {
                const currentChunk = e.target.closest('.chunk-container');
                const showX = !currentChunk.querySelector('.x-item').classList.contains('hidden');
                const newChunk = createNewChunk('', '', '', false, showX);
                currentChunk.parentNode.insertBefore(newChunk, currentChunk.nextSibling);
                const newInput = newChunk.querySelector('.x-input');
                newInput.focus();
                autoResizeTextarea(newInput);
                e.preventDefault(); // 防止事件冒泡
            }
        });

        // 初始化现有文本框的自动调整
        document.querySelectorAll('.x-input, .y-input, .revision-input').forEach(textarea => {
            autoResizeTextarea(textarea);
        });

        // 替换原来的chunk选择事件监听器
        document.addEventListener('click', handleChunkSelection);

        // 修改开始创作按钮点击事件
        actionBtn.addEventListener('click', handleCreateAction);
    
        // 修改接受和拒绝按钮的事件处理
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('accept-btn') || e.target.classList.contains('reject-btn')) {
                const chunk = e.target.closest('.chunk-container');
                handleRevision(chunk, e.target.classList.contains('accept-btn'));
            }
        });

        // 添加删除按钮的事件处理
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('delete-x-btn')) {
                const chunkToDelete = e.target.closest('.chunk-container');
                const allChunks = document.querySelectorAll('.chunk-container');
                
                // 如果这是最后一个chunk，不允许删除
                if (allChunks.length === 1) {
                    return;
                }
                
                // 如果chunk被选中，从selectedChunks中移除
                if (selectedChunks.includes(chunkToDelete)) {
                    selectedChunks = selectedChunks.filter(c => c !== chunkToDelete);
                }
                
                chunkToDelete.remove();
                e.preventDefault(); // 防止事件冒泡
            }
        });

        // 由prompt.js初始化chunk
        // const initialChunk = createNewChunk('', '', '');
        // chunkContainer.appendChild(initialChunk);

        // 添加批量操作按钮的事件监听
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('batch-accept-btn')) {
                handleBatchRevision(true);
            } else if (e.target.classList.contains('batch-reject-btn')) {
                handleBatchRevision(false);
            }
        });
    }

    // 添加mode切换的处理函数
    function handleModeChange(newMode) {
        // 如果有未处理的创作，阻止切换
        if (isWriting) {
            return false;
        }

        // 清除当前选择
        selectedChunks.forEach(chunk => chunk.classList.remove('selected'));
        selectedChunks = [];
        lastSelectedIndex = -1;

        // 更新当前mode
        currentMode = newMode;
        
        return true;
    }

    // 将handleModeChange暴露给外部
    window.handleContentModeChange = handleModeChange;

    initializeEventListeners();
}); 