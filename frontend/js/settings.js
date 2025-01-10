import { showToast } from './utils.js';

let previousMode = null;
let modelConfigs = null;

// Create and append the settings popup HTML to the document
function createSettingsPopup() {
    const overlay = document.createElement('div');
    overlay.className = 'settings-overlay';
    
    const popup = document.createElement('div');
    popup.className = 'settings-popup';
    
    // Get settings from localStorage
    const settings = JSON.parse(localStorage.getItem('settings') || '{}');
    
    popup.innerHTML = `
        <div class="settings-header">
            <div class="header-content">
                <h3>设置</h3>
                <p class="subtitle">配置系统参数和模型选择</p>
            </div>
            <button class="settings-close">&times;</button>
        </div>
        <div class="settings-content">
            <div class="settings-section">
                <h4>系统参数</h4>
                <div class="setting-item">
                    <label for="maxThreadNum">最大线程数</label>
                    <input type="number" id="maxThreadNum" min="1" max="20" value="${settings.MAX_THREAD_NUM}">
                </div>
                <div class="setting-item">
                    <label for="maxNovelSummaryLength">导入小说的最大长度</label>
                    <input type="number" id="maxNovelSummaryLength" min="10000" max="1000000" value="${settings.MAX_NOVEL_SUMMARY_LENGTH}">
                </div>
            </div>
            <div class="settings-section">
                <h4>模型设置</h4>
                <div class="setting-item">
                    <label for="defaultMainModel">主模型</label>
                    <div class="model-select-group">
                        <select id="defaultMainModel"></select>
                        <button class="test-model-btn" data-for="defaultMainModel">测试</button>
                    </div>
                </div>
                <div class="setting-item">
                    <label for="defaultSubModel">辅助模型</label>
                    <div class="model-select-group">
                        <select id="defaultSubModel"></select>
                        <button class="test-model-btn" data-for="defaultSubModel">测试</button>
                    </div>
                </div>
            </div>
        </div>
        <div class="settings-footer">
            <button class="save-settings">保存设置</button>
        </div>
    `;
    
    overlay.appendChild(popup);
    document.body.appendChild(overlay);
    
    // Add event listeners
    const closeBtn = popup.querySelector('.settings-close');
    closeBtn.addEventListener('click', hideSettings);
    
    const saveBtn = popup.querySelector('.save-settings');
    saveBtn.addEventListener('click', () => {
        saveSettings();
        hideSettings();
    });
    
    // Add test button event listeners
    const testButtons = popup.querySelectorAll('.test-model-btn');
    testButtons.forEach(btn => {
        btn.addEventListener('click', async () => {
            const selectId = btn.dataset.for;
            const select = document.getElementById(selectId);
            const selectedModel = select.value;
            
            if (!selectedModel) {
                showToast('请先选择一个模型', 'error');
                return;
            }
            
            btn.disabled = true;
            btn.textContent = '测试中...';
            
            try {
                const response = await fetch(`${window._env_?.SERVER_URL}/test_model`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        provider_model: selectedModel
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showToast('模型测试成功', 'success');
                } else {
                    showToast(`模型测试失败: ${result.error}`, 'error');
                }
            } catch (error) {
                showToast(`测试请求失败: ${error.message}`, 'error');
            } finally {
                btn.disabled = false;
                btn.textContent = '测试';
            }
        });
    });
    
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            hideSettings();
        }
    });
    
    return overlay;
}

export async function loadModelConfigs() {
    try {
        const response = await fetch(`${window._env_?.SERVER_URL}/setting`);
        const settings = await response.json();
        modelConfigs = settings.models;
        
        // Initialize localStorage settings if not exists
        if (!localStorage.getItem('settings')) {
            localStorage.setItem('settings', JSON.stringify({
                MAIN_MODEL: settings.MAIN_MODEL,
                SUB_MODEL: settings.SUB_MODEL,
                MAX_THREAD_NUM: settings.MAX_THREAD_NUM,
                MAX_NOVEL_SUMMARY_LENGTH: settings.MAX_NOVEL_SUMMARY_LENGTH
            }));
        }
    } catch (error) {
        console.error('Error loading settings:', error);
        showToast('加载设置失败', 'error');
    }
}

function updateModelSelects() {
    const mainModelSelect = document.getElementById('defaultMainModel');
    const subModelSelect = document.getElementById('defaultSubModel');
    
    if (!mainModelSelect || !subModelSelect || !modelConfigs) return;
    
    mainModelSelect.innerHTML = '';
    subModelSelect.innerHTML = '';
    
    // Filter out special config keys and only process provider/models pairs
    Object.entries(modelConfigs).forEach(([provider, models]) => {
        models.forEach(model => {
            const option = document.createElement('option');
            option.value = `${provider}/${model}`;
            option.textContent = `${provider}/${model}`;
            
            mainModelSelect.appendChild(option.cloneNode(true));
            subModelSelect.appendChild(option.cloneNode(true));
        });
    });
}

function loadCurrentSettings() {
    const settings = JSON.parse(localStorage.getItem('settings'));
    const mainModelSelect = document.getElementById('defaultMainModel');
    const subModelSelect = document.getElementById('defaultSubModel');
    
    if (mainModelSelect.options.length > 0) {
        mainModelSelect.value = settings.MAIN_MODEL;
    }
    if (subModelSelect.options.length > 0) {
        subModelSelect.value = settings.SUB_MODEL;
    }

    // Load max thread number and novel summary length
    document.getElementById('maxThreadNum').value = settings.MAX_THREAD_NUM;
    document.getElementById('maxNovelSummaryLength').value = settings.MAX_NOVEL_SUMMARY_LENGTH;
}

function saveSettings() {
    const settings = {
        MAIN_MODEL: document.getElementById('defaultMainModel').value,
        SUB_MODEL: document.getElementById('defaultSubModel').value,
        MAX_THREAD_NUM: parseInt(document.getElementById('maxThreadNum').value),
        MAX_NOVEL_SUMMARY_LENGTH: parseInt(document.getElementById('maxNovelSummaryLength').value)
    };
    
    localStorage.setItem('settings', JSON.stringify(settings));
    showToast('设置已保存', 'success');
}

export function showSettings(_previousMode) {
    // Store current mode before switching to settings
    previousMode = _previousMode;
    
    let overlay = document.querySelector('.settings-overlay');
    if (!overlay) {
        overlay = createSettingsPopup();
        updateModelSelects();
    }

    loadCurrentSettings();
    overlay.style.display = 'block';
}

function hideSettings() {
    const overlay = document.querySelector('.settings-overlay');
    if (overlay) {
        overlay.style.display = 'none';
        
        // Switch back to previous mode
        if (previousMode) {
            const previousTab = document.querySelector(`.mode-tab[data-value="${previousMode}"]`);
            if (previousTab) {
                previousTab.click();
            }
        }
    }
}