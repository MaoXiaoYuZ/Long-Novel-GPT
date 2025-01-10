// Create and append the popup HTML to the document
import { saveDataToStorage, showToast, stopStream } from './utils.js';
import jsyaml from 'https://cdn.skypack.dev/js-yaml';

// Add AbortController for fetch requests
let currentFetchController = null;
let currentStreamId = null;

function createNovelSelectPopup() {
    const overlay = document.createElement('div');
    overlay.className = 'novel-select-overlay';
    
    const popup = document.createElement('div');
    popup.className = 'novel-select-popup';
    
    popup.innerHTML = `
        <div class="novel-select-header">
            <div class="header-content">
                <h3>选择小说</h3>
                <p class="subtitle">成功从模仿开始，选择一本经典小说来作为模板进行创作！</p>
            </div>
            <button class="novel-select-close">&times;</button>
        </div>
        <div class="novel-list-section">
            <h4 class="section-title">示例小说</h4>
            <div class="novel-list">
                <!-- Novel items will be dynamically added here -->
            </div>
        </div>
        <div class="file-import-section">
            <h4 class="section-title">导入自己的小说</h4>
            <input type="file" id="txtFileInput" accept=".txt" style="display: none">
            <button class="import-btn">导入TXT文件</button>
            <div class="progress-msg" style="display: none"></div>
        </div>
    `;
    
    overlay.appendChild(popup);
    document.body.appendChild(overlay);
    
    // Add event listeners
    const closeBtn = popup.querySelector('.novel-select-close');
    closeBtn.addEventListener('click', hideNovelSelect);
    
    const importBtn = popup.querySelector('.import-btn');
    const fileInput = popup.querySelector('#txtFileInput');
    
    importBtn.addEventListener('click', () => {
        fileInput.click();
    });
    
    fileInput.addEventListener('change', handleFileSelect);
    
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            hideNovelSelect();
        }
    });
    
    return overlay;
}

// Show the novel selection popup
export function showNovelSelect() {
    let overlay = document.querySelector('.novel-select-overlay');
    if (!overlay) {
        overlay = createNovelSelectPopup();
    }
    
    // Load novels (you'll need to implement this based on your backend)
    loadNovels();
    
    overlay.style.display = 'block';
}

// Hide the novel selection popup
export function hideNovelSelect() {
    const overlay = document.querySelector('.novel-select-overlay');
    if (overlay) {
        overlay.style.display = 'none';
        
        // Abort any ongoing fetch request
        if (currentFetchController) {
            currentFetchController.abort();
            currentFetchController = null;
        }
        
        // Switch to outline tab
        const outlineTab = document.querySelector('.mode-tab[data-value="outline"]');
        if (outlineTab) {
            outlineTab.click();
        }
    }
}

// Load novels from example_novels directory
async function loadNovels() {
    try {
        const novelFiles = ['斗破苍穹.yaml', '凡人修仙传.yaml',];
        
        const novels = await Promise.all(novelFiles.map(async (fileName) => {
            try {
                const response = await fetch(`data/example_novels/${fileName}`);
                const yamlText = await response.text();
                const novelData = jsyaml.load(yamlText);
                return {
                    title: fileName.replace('.yaml', ''),
                    data: novelData,
                    description: novelData.description || '暂无简介'
                };
            } catch (error) {
                console.error(`Error loading novel ${fileName}:`, error);
                return null;
            }
        }));

        displayNovels(novels.filter(novel => novel !== null));
    } catch (error) {
        console.error('Error loading novels:', error);
        showToast('加载示例小说失败', 'error');
    }
}

// Display novels in the popup
function displayNovels(novels) {
    const novelList = document.querySelector('.novel-list');
    if (!novelList) return;
    
    novelList.innerHTML = '';
    
    novels.forEach(novel => {
        const novelItem = document.createElement('div');
        novelItem.className = 'novel-item';
        novelItem.innerHTML = `
            <h4>${novel.title}</h4>
            <p>${novel.description || '暂无简介'}</p>
        `;
        
        novelItem.addEventListener('click', () => {
            selectNovel(novel);
        });
        
        novelList.appendChild(novelItem);
    });
}

// Save novel data to storage
function saveNovelData(data) {
    // Save outline data
    saveDataToStorage('outline', null, data.outline.chunks, data.outline.context);
    
    // Save plot data for each chapter
    Object.entries(data.plot).forEach(([chapterName, chapterData]) => {
        saveDataToStorage('plot', chapterName, chapterData.chunks, chapterData.context);
    });
    
    // Save draft data for each chapter
    Object.entries(data.draft).forEach(([chapterName, chapterData]) => {
        saveDataToStorage('draft', chapterName, chapterData.chunks, chapterData.context);
    });
}

// Handle novel selection
function selectNovel(novel) {
    const data = novel.data;
    saveNovelData(data);
    
    // Hide the popup
    hideNovelSelect(); // This will also switch to the outline tab
    
    // Dispatch an event to notify other components
    const event = new CustomEvent('novel-selected', { detail: novel });
    document.dispatchEvent(event);
}

// Handle file selection and upload
async function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    // Reset file input for next use
    event.target.value = '';

    const reader = new FileReader();
    reader.onload = async (e) => {
        let content;
        try {
            content = e.target.result;
            // Check if content is garbled (contains lots of  characters)
            if (content.split('').length > content.length * 0.1) {
                // If garbled, try reading again with GBK encoding
                const response = await fetch(URL.createObjectURL(file));
                const buffer = await response.arrayBuffer();
                const decoder = new TextDecoder('gbk');
                content = decoder.decode(buffer);
            }
        } catch (error) {
            console.error('Error reading file:', error);
            showToast('读取文件失败，请重试', 'error');
            return;
        }

        const novelName = file.name.replace('.txt', '');
        
        try {
            const progressMsg = document.querySelector('.progress-msg');
            progressMsg.style.display = 'block';
            progressMsg.textContent = '开始处理小说...';
            // Create new AbortController for this fetch request
            if (currentFetchController) {
                currentFetchController.abort();
                await stopStream(currentStreamId);
            }
            currentFetchController = new AbortController();
            currentStreamId = null;

            const settings = JSON.parse(localStorage.getItem('settings'));
            const response = await fetch(`${window._env_?.SERVER_URL}/summary`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    content: content,
                    novel_name: novelName,
                    main_model: settings.MAIN_MODEL,
                    sub_model: settings.SUB_MODEL,
                    settings:{
                        MAX_THREAD_NUM: settings.MAX_THREAD_NUM,
                        MAX_NOVEL_SUMMARY_LENGTH: settings.MAX_NOVEL_SUMMARY_LENGTH
                    }
                }),
                signal: currentFetchController.signal
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            try {
                while (true) {
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
                                
                                // Update progress message
                                if (data.progress_msg) {
                                    progressMsg.textContent = data.progress_msg;
                                }

                                // Save the final data when we have all components
                                if (data.outline && data.plot && data.draft) {
                                    saveNovelData(data);
                                    progressMsg.textContent = '处理完成！';
                                    setTimeout(() => {
                                        hideNovelSelect();
                                    }, 1500);
                                }
                            } catch (e) {
                                console.error('Error parsing SSE data:', e);
                            }
                        }
                    }
                    buffer = lines[0] || '';
                }
            } catch (error) {
                if (error.name === 'AbortError') {
                    console.log('Fetch aborted');
                    progressMsg.textContent = '已取消处理';
                    showToast('已取消处理', 'warning');
                    await stopStream(currentStreamId);
                } else {
                    throw error;
                }
            }
        } catch (error) {
            if (error.name !== 'AbortError') {
                console.error('Error processing novel:', error);
                const progressMsg = document.querySelector('.progress-msg');
                progressMsg.textContent = '处理失败，请重试';
            }
        } finally {
            currentFetchController = null;
            currentStreamId = null;
        }
    };
    reader.readAsText(file);
}