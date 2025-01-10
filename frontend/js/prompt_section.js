import { createNewChunk, updateChunksContent, showToast, toggleLeftPanel, getStorageKey, saveDataToStorage, getDataFromStorage } from './utils.js';
import jsyaml from 'https://cdn.skypack.dev/js-yaml';
import { showNovelSelect } from './novel_select.js';
import { showSettings, loadModelConfigs } from './settings.js';

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
    const writeMode = document.getElementById('writeMode');
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
                if (writeMode.value === 'draft') {
                    updateChunksContent([[example.x, '', null]], chunks, true);
                } else {
                    updateChunksContent([['', '', null]], chunks, true);
                    document.querySelector('.left-panel-input').value = example.x;
                }
            }
        });
        container.appendChild(card);
    });
}

// Add window size configurations
const WINDOW_SIZES = {
    'outline': [
        { x: 500, y: 500, label: '500字' },
        { x: 1000, y: 1000, label: '1000字' },
        { x: 1000, y: 1500, label: '1500字' }
    ],
    'plot': [
        { x: 100, y: 200, label: '200字' },
        { x: 250, y: 500, label: '500字' },
        { x: 500, y: 1000, label: '1000字' },
        { x: 1000, y: 1500, label: '1500字' }
    ],
    'draft': [
        { x: 250, y: 500, label: '500字' },
        { x: 100, y: 200, label: '200字' },
        { x: 500, y: 1000, label: '1000字' },
        { x: 1000, y: 1500, label: '1500字' }
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

    // 初始化时设置第一个非novel tab为active
    const firstNonNovelTab = Array.from(modeTabs).find(tab => !['novel', 'settings'].includes(tab.dataset.value));
    if (firstNonNovelTab) {
        firstNonNovelTab.classList.add('active');
        writeMode.value = firstNonNovelTab.dataset.value;
        updateWindowSizeOptions(firstNonNovelTab.dataset.value);
    }

    modeTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const newMode = tab.dataset.value;

            // 调用content_section.js的处理函数
            if (!window.handleContentModeChange(newMode)) {
                showToast('请先处理所有创作', 'warning');
                return;
            }
            
            // 如果点击的是"选择小说"标签
            if (newMode === 'novel') {
                // 更新UI状态
                modeTabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                writeMode.value = newMode;
                
                showNovelSelect();
                return;
            }

            // 如果点击的是"设置"标签
            if (newMode === 'settings') {
                // 更新UI状态
                modeTabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                let previousMode = writeMode.value;
                writeMode.value = newMode;
                
                showSettings(previousMode);
                return;
            }

            // Save current state
            const currentMode = writeMode.value;
            let currentChapter = currentMode === 'outline' ? null : document.getElementById('chapterSelect').value;
            if (!['novel', 'settings'].includes(currentMode)) {
                const currentChunks = Array.from(document.querySelectorAll('.chunk-container')).map(chunk => [
                    chunk.querySelector('.x-input').value,
                    chunk.querySelector('.y-input').value,
                    chunk.querySelector('.revision-item').classList.contains('visible') ? 
                        chunk.querySelector('.revision-input').value : null
                ]);
                
                let currentContext = '';
                if (currentMode !== 'draft') {
                    const leftPanelInput = document.querySelector('.left-panel-input');
                    if (leftPanelInput) {
                        currentContext = leftPanelInput.value;
                    }
                }

                // 保存当前状态
                saveDataToStorage(currentMode, currentChapter, currentChunks, currentContext);

                // 根据模式切换更新内容
                if (currentMode === 'outline') {
                    updateChapterSelect(currentChunks);
                }
            }

            // 更新UI状态
            modeTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            writeMode.value = newMode;

            if (['settings', ].includes(currentMode)) return;
            
            // 更新章节选择器
            document.querySelector('.chapter-selection').style.display = 
                newMode === 'outline' ? 'none' : 'block';
            

            // 更新列标题
            updateColumnHeaders(newMode);
            
            // 更新prompts选项
            updatePromptOptions(newMode);
            
            // 更新示例卡片
            updateExampleCards(newMode);
            
            // 重新渲染chunks，这里的渲染是基于新的writemode，所以需要更新currentChapter
            currentChapter = newMode === 'outline' ? null : document.getElementById('chapterSelect').value;
            renderChunks(currentChapter);

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
                rightHeaderSpan.textContent = '章节';
                break;
            case 'plot':
                leftHeaderSpan.textContent = '章节';
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

// Add new function to handle chapter selection
function handleChapterChange(chapter) {
    const mode = document.getElementById('writeMode').value;
    if (mode !== 'outline') {
        renderChunks(chapter);
    }
}

// Update renderChunks to use consolidated storage
function renderChunks(chapter = null) {
    const mode = document.getElementById('writeMode').value;
    const showLeftPanel = mode !== 'draft';
    
    // Toggle left panel visibility
    toggleLeftPanel(showLeftPanel);
    
    // Get saved data
    const savedData = getDataFromStorage(mode, chapter);

    if (mode === 'plot'){
        const outlineData = getDataFromStorage('outline');
        const chapterContent = outlineData.chunks.find(chunk => 
            chunk[1].split('\n')[0] === chapter
        );
        if (chapterContent && chapterContent[1] !== '') {
            if (savedData.context === '')savedData.context = chapterContent[1];
            else if (savedData.context !== chapterContent[1]){
                showToast('章节内容和<创作章节>中不一致', 'warning');
            }
        }else{
            showToast('章节内容未找到', 'warning');
        }
    }

    if (mode === 'draft'){
        const plotData = getDataFromStorage('plot', chapter);
        const new_plot_text = plotData.chunks.map(chunk => chunk[1]).join('\n');
        if (plotData.chunks.length > 0 && new_plot_text !== ''){
            const old_plot_text = savedData.chunks.map(chunk => chunk[0]).join('\n');
            if (old_plot_text === ''){
                savedData.chunks = [[new_plot_text, '', null]];
            }
            else if (old_plot_text !== new_plot_text){
                showToast('剧情内容和<创作剧情>中不一致', 'warning');
            }
        }else{
            showToast('未找到该章节的剧情内容', 'warning');
        }
    }
    
    // Update left panel content if visible
    if (showLeftPanel) {
        const leftPanelInput = document.querySelector('.left-panel-input');
        if (leftPanelInput) {
            leftPanelInput.value = savedData.context || '';
        }
    }
    
    // Get and render chunks
    let chunks = savedData.chunks;
    if (chunks.length === 0) chunks = [['', '', null]];
    updateChunksContent(chunks, Array.from(document.querySelectorAll('.chunk-container')), true);
}

function initChunksManagement() {    
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
function initGuideSection() {
    const guideSection = document.querySelector('.guide-section');
    const toggleGuideBtn = document.querySelector('.toggle-guide');

    if (toggleGuideBtn) {
        toggleGuideBtn.addEventListener('click', () => {
            guideSection.classList.toggle('collapsed');
        });
    }
}

// Modify initChapterSelection to handle chapter changes
function initChapterSelection() {
    const chapterSelect = document.getElementById('chapterSelect');
    const chapterSelection = document.querySelector('.chapter-selection');
    
    if (chapterSelect) {
        // Show/hide chapter selection based on mode
        const mode = document.getElementById('writeMode').value;
        chapterSelection.style.display = mode === 'outline' ? 'none' : 'block';
        
        chapterSelect.addEventListener('change', (e) => {
            handleChapterChange(e.target.value);
        });
    }
}

// 新增函数：更新章节选择器
function updateChapterSelect(chunks) {
    const chapterSelect = document.getElementById('chapterSelect');
    chapterSelect.innerHTML = '';

    // Check if any chunk has non-empty content
    const hasValidChunks = chunks.some(chunk => chunk[1].trim());
    if (!hasValidChunks) {
        chunks = [['', '默认章节名', null]];
    }
    
    chunks.forEach((chunk, index) => {
        if (chunk[1].trim()) {
            const chapterName = chunk[1].split('\n')[0];
            const option = document.createElement('option');
            option.value = chapterName;
            option.textContent = chapterName;
            option.title = chapterName;
            chapterSelect.appendChild(option);
        }
    });
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    loadModelConfigs();
    initModeHandlers();
    initPromptHandlers();
    initChunksManagement();
    initCopyButtons();
    initExamplesSection();
    initGuideSection();
    initChapterSelection();
}); 

