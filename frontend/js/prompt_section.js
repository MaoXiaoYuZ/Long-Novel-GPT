import { createNewChunk, updateChunksContent, showToast } from './utils.js';
import jsyaml from 'https://cdn.skypack.dev/js-yaml';

let examples = null;

let prompts = null;

async function fetchPrompts() {
    try {
        const response = await fetch(`${window._env_?.SERVER_URL}/prompts`);
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching prompts:', error);
        return null;
    }
}

function updateTextArea(content) {
    const textarea = document.querySelector('.prompt-input textarea');
    if (textarea) {
        textarea.value = content;
    }
}

async function loadExamples() {
    try {
        const response = await fetch('data/examples.yaml');
        const yamlText = await response.text();
        examples = jsyaml.load(yamlText);
    } catch (error) {
        console.error('Error loading examples:', error);
        showToast('加载示例失败', 'error');
    }
}

function updateExampleCards(mode) {
    const container = document.querySelector('.examples-container');
    if (!container || !examples) return;
    
    container.innerHTML = '';

    // 根据mode选择对应的examples
    const modeToExamples = {
        'outline': 'summary_examples',
        'plot': 'outline_examples',
        'draft': 'plot_examples'
    };
    
        
    const modeExamples = examples[modeToExamples[mode]] || [];
    modeExamples.forEach(example => {
        const card = document.createElement('div');
        card.className = 'example-card';
        card.innerHTML = `
            <h4>${example.title}</h4>
            <p>${example.subtitle}</p>
        `;
        card.addEventListener('click', () => {
            const chunks = Array.from(document.querySelectorAll('.chunk-container'));
            if (chunks.length > 0) {
                updateChunksContent([[example.x, '', null]], chunks, true);
            }
        });
        container.appendChild(card);
    });
}

// Add window size configurations
const WINDOW_SIZES = {
    'outline': [
        { x: 4000, y: 4000, label: '4千字' }
    ],
    'plot': [
        { x: 100, y: 200, label: '2百字' },
        { x: 250, y: 500, label: '5百字' },
        { x: 500, y: 1000, label: '1千字' },
        { x: 1000, y: 2000, label: '2千字' }
    ],
    'draft': [
        { x: 250, y: 500, label: '5百字' },
        { x: 500, y: 1000, label: '1千字' },
        { x: 1000, y: 2000, label: '2千字' },
        { x: 1500, y: 3000, label: '3千字' }
    ]
};

// Update the window size select options based on mode
function updateWindowSizeOptions(mode) {
    const windowSizeSelect = document.querySelector('.context-window-select');
    windowSizeSelect.innerHTML = '';
    
    WINDOW_SIZES[mode].forEach(size => {
        const option = document.createElement('option');
        option.value = JSON.stringify({ x: size.x, y: size.y });
        option.textContent = size.label;
        windowSizeSelect.appendChild(option);
    });
}

function initModeHandlers() {
    const writeMode = document.getElementById('writeMode');
    const leftHeader = document.querySelector('.left-header');
    const rightHeader = document.querySelector('.right-header');
    const modeTabs = document.querySelectorAll('.mode-tab');

    // 初始化时设置第一个tab为active
    modeTabs[0].classList.add('active');
    writeMode.value = modeTabs[0].dataset.value;
    updateWindowSizeOptions(modeTabs[0].dataset.value); // 初始化窗口大小选项

    modeTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const newMode = tab.dataset.value;
            
            // 调用content_section.js的处理函数
            if (!window.handleContentModeChange(newMode)) {
                showToast('请先处理所有创作', 'warning');
                return;
            }

            // 保存当前chunks数据
            const currentChunks = Array.from(document.querySelectorAll('.chunk-container'));
            const chunksData = currentChunks.map(chunk => [
                chunk.querySelector('.x-input').value,
                chunk.querySelector('.y-input').value,
                chunk.querySelector('.revision-item').classList.contains('visible') ? 
                    chunk.querySelector('.revision-input').value : null
            ]);
            saveChunksToStorage(writeMode.value, chunksData);
            
            // 更新UI状态
            modeTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            writeMode.value = newMode;

            // 更新列标题
            updateColumnHeaders(newMode);
            
            // 更新prompts选项
            updatePromptOptions(newMode);
            
            // 更新示例卡片
            updateExampleCards(newMode);
            
            // 重新渲染chunks
            renderChunks();

            // 更新窗口大小选项
            updateWindowSizeOptions(newMode);
        });
    });

    function updateColumnHeaders(mode) {
        const leftHeaderSpan = leftHeader.querySelector('span');
        const rightHeaderSpan = rightHeader.querySelector('span');
        
        switch(mode) {
            case 'outline':
                leftHeaderSpan.textContent = '小说简介';
                rightHeaderSpan.textContent = '大纲';
                break;
            case 'plot':
                leftHeaderSpan.textContent = '大纲';
                rightHeaderSpan.textContent = '剧情';
                break;
            case 'draft':
                leftHeaderSpan.textContent = '剧情';
                rightHeaderSpan.textContent = '正文';
                break;
        }
    }
}

function initPromptHandlers() {
    const promptSelect = document.querySelector('.prompt-actions .select-wrapper select');
    const writeMode = document.getElementById('writeMode');

    fetchPrompts().then(data => {
        prompts = data;
        if (prompts) {
            updatePromptOptions(writeMode.value);
        }
    });

    writeMode.addEventListener('change', () => {
        updatePromptOptions(writeMode.value);
    });

    promptSelect.addEventListener('change', (e) => {
        const selectedMode = writeMode.value;
        const selectedPrompt = e.target.value;
        
        if (prompts && prompts[selectedMode] && prompts[selectedMode][selectedPrompt]) {
            updateTextArea(prompts[selectedMode][selectedPrompt].content);
        }
    });
}

function updatePromptOptions(mode) {
    const promptSelect = document.querySelector('.prompt-actions .select-wrapper select');
    promptSelect.innerHTML = '';
    
    if (prompts && prompts[mode]) {
        // Use prompt_names array for ordering if available, otherwise fallback to Object.keys
        const promptNames = prompts[mode].prompt_names || Object.keys(prompts[mode]);
        
        promptNames.forEach(promptName => {
            // Skip the prompt_names field itself
            if (promptName === 'prompt_names') return;
            
            // Only create option if the prompt exists
            if (prompts[mode][promptName]) {
                const option = document.createElement('option');
                option.value = promptName;
                option.textContent = promptName;
                promptSelect.appendChild(option);
            }
        });
        
        // Trigger change event to update textarea with first option
        promptSelect.dispatchEvent(new Event('change'));
    }
}

// Storage management for chunks data
function saveChunksToStorage(mode, chunks) {
    const key = `chunks_${mode}`;
    const chunksJson = JSON.stringify(chunks);
    try {
        localStorage.setItem(key, chunksJson);
        // console.log(`Saved ${mode} chunks to localStorage: ${chunksJson}`);
        showToast('数据已保存', 'success');
    } catch (e) {
        console.error('Error saving to localStorage:', e);
        if (e.name === 'QuotaExceededError') {
            showToast('存储空间已满，请导出数据后清理存储空间', 'error');
        } else {
            showToast('保存失败', 'error');
        }
    }
}

function deleteChunksStorage(mode) {
    const key = `chunks_${mode}`;
    try {
        localStorage.removeItem(key);
        console.log(`Deleted storage: ${key}`);
    } catch (e) {
        console.error('Error deleting from localStorage:', e);
    }
}

function getChunksFromStorage(mode) {
    const key = `chunks_${mode}`;
    try {
        const value = localStorage.getItem(key);
        if (!value) return [];
        return JSON.parse(value);
    } catch (e) {
        console.error('Error getting chunks from localStorage:', e);
        return [];
    }
}

function renderChunks() {
    // 从storage中获取chunks数据，必须至少有一个chunk
    let saveChunks = getChunksFromStorage(writeMode.value);
    if (saveChunks.length === 0) saveChunks = [['', '', null]];
    updateChunksContent(saveChunks, Array.from(document.querySelectorAll('.chunk-container')), true);
    // console.log(`Render ${writeMode.value} chunks: ${saveChunks}`);
}

function initChunksManagement() {
    deleteChunksStorage; // 闭包, 用于debug
    // deleteChunksStorage('outline');deleteChunksStorage('plot');deleteChunksStorage('draft');
    
    const chunkContainer = document.getElementById('chunkContainer');
    const initialChunk = createNewChunk('', '', '');
    chunkContainer.appendChild(initialChunk);

    renderChunks();
}

function fallbackCopyToClipboard(text) {
    // 创建临时文本区域
    const textArea = document.createElement('textarea');
    textArea.value = text;
    
    // 确保文本区域在视图之外
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
      document.execCommand('copy');
    } catch (err) {
      console.error('复制失败:', err);
      throw err;
    }
    
    document.body.removeChild(textArea);
}


// 添加复制功能
function initCopyButtons() {
    document.querySelectorAll('.copy-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const column = btn.dataset.column;
            const selector = column === 'left' ? '.x-input' : '.y-input';
            const inputs = Array.from(document.querySelectorAll(selector));
            const text = inputs.map(input => input.value.trim()).filter(Boolean).join('\n');
            
            if (!text) {
                showToast('没有可复制的内容', 'warning');
                return;
            }

            if (navigator.clipboard) {
                navigator.clipboard.writeText(text).then(() => {
                    showToast('复制成功', 'success');
                }).catch(err => {
                    console.error('复制失败:', err);
                    showToast('复制失败', 'error');
                });
            } else {
                try{
                    fallbackCopyToClipboard(text);
                    showToast('复制成功', 'success');
                }catch(err){
                    console.error('Clipboard API not supported');
                    showToast('当前浏览器不支持复制功能，请手动复制', 'error');
                }
            }
        });
    });
}

// 处理示例卡片点击事件和拖动滚动
async function initExamplesSection() {
    await loadExamples();
    // 初始化显示第一个mode的示例
    const initialMode = document.getElementById('writeMode').value;
    updateExampleCards(initialMode);

    // 添加折叠功能
    const toggleBtn = document.querySelector('.toggle-examples');
    const examplesSection = document.querySelector('.examples-section');
    
    toggleBtn.addEventListener('click', () => {
        examplesSection.classList.toggle('collapsed');
        // 可选：保存用户偏好
        localStorage.setItem('examples-collapsed', examplesSection.classList.contains('collapsed'));
    });

    // 恢复用户的折叠偏好
    const isCollapsed = localStorage.getItem('examples-collapsed') === 'true';
    if (isCollapsed) {
        examplesSection.classList.add('collapsed');
    }
}

// 添加使用指南折叠功能
const guideSection = document.querySelector('.guide-section');
const toggleGuideBtn = document.querySelector('.toggle-guide');

if (toggleGuideBtn) {
    toggleGuideBtn.addEventListener('click', () => {
        guideSection.classList.toggle('collapsed');
    });
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    initModeHandlers();
    initPromptHandlers();
    initChunksManagement();
    initCopyButtons();
    initExamplesSection();
}); 