export class ChatMessagesUI {
    constructor() {
        this.modal = this.createModal();
        this.messageContainer = this.modal.querySelector('.chat-messages');
        this.setupEventListeners();
    }

    createModal() {
        const modal = document.createElement('div');
        modal.className = 'chat-modal';
        modal.innerHTML = `
            <div class="chat-modal-content">
                <div class="chat-modal-header">
                    <h2>Prompt Messages</h2>
                    <button class="close-btn">&times;</button>
                </div>
                <div class="chat-messages"></div>
            </div>
        `;
        document.body.appendChild(modal);
        return modal;
    }

    setupEventListeners() {
        const closeBtn = this.modal.querySelector('.close-btn');
        closeBtn.addEventListener('click', () => this.hide());

        // Close modal when clicking outside
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.hide();
            }
        });
    }

    show(messages) {
        this.messageContainer.innerHTML = '';
        messages.forEach(msg => {
            const messageEl = document.createElement('div');
            messageEl.className = `chat-message ${msg.role}`;
            
            const contentEl = document.createElement('div');
            contentEl.className = 'message-content';
            contentEl.textContent = msg.content;
            
            const roleEl = document.createElement('div');
            roleEl.className = 'message-role';
            roleEl.textContent = msg.role.charAt(0).toUpperCase() + msg.role.slice(1);
            
            messageEl.appendChild(roleEl);
            messageEl.appendChild(contentEl);
            this.messageContainer.appendChild(messageEl);
        });
        
        this.modal.style.display = 'flex';
    }

    hide() {
        this.modal.style.display = 'none';
    }
}

// Test code
const testMessages = [
    { role: 'system', content: 'You are a helpful novel writing assistant.' },
    { role: 'user', content: '请帮我写一个科幻小说的开头。' },
    { role: 'assistant', content: '在2157年的一个寒冷清晨，太空站"织女"号的警报突然响起...' },
];

// Create button for testing
// const testButton = document.createElement('button');
// testButton.textContent = '显示Prompt';
// testButton.className = 'show-prompt-btn';
// document.querySelector('.prompt-actions').appendChild(testButton);

// const chatUI = new ChatMessagesUI();
// testButton.addEventListener('click', () => {
//     chatUI.show(testMessages);
// }); 