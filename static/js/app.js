// Enhanced Banking Chat Interface
class BankingChatInterface {
    constructor() {
        this.chatHistory = [];
        this.isTyping = false;
        this.sessionId = this.getSessionId();
        
        // DOM elements
        this.chatForm = document.getElementById('chat-form');
        this.messageInput = document.getElementById('message-input');
        this.chatMessages = document.getElementById('chat-messages');
        this.typingIndicator = document.getElementById('typing-indicator');
        this.sendButton = document.getElementById('send-button');
        this.charCount = document.getElementById('char-count');
        
        this.init();
    }
    
    init() {
        this.loadChatHistory();
        this.setupEventListeners();
        this.autoResizeTextarea();
        this.messageInput?.focus();
    }
    
    setupEventListeners() {
        // Form submission
        this.chatForm?.addEventListener('submit', (e) => this.handleFormSubmit(e));
        
        // Textarea auto-resize and character count
        this.messageInput?.addEventListener('input', () => {
            this.autoResizeTextarea();
            this.updateCharCount();
        });
        
        // Enter key handling
        this.messageInput?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleFormSubmit(e);
            }
        });
        
        // Global keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Ctrl+L to clear chat
            if (e.ctrlKey && e.key === 'l') {
                e.preventDefault();
                this.clearChat();
            }
            
            // Escape to focus on input
            if (e.key === 'Escape') {
                this.messageInput?.focus();
            }
        });
        
        // Network status
        window.addEventListener('online', () => {
            this.showToast('Connection restored', 'success');
        });
        
        window.addEventListener('offline', () => {
            this.showToast('You are offline. Messages will be sent when connection is restored.', 'warning');
        });
    }
    
    autoResizeTextarea() {
        if (this.messageInput) {
            this.messageInput.style.height = 'auto';
            this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
        }
    }
    
    updateCharCount() {
        if (!this.charCount || !this.messageInput) return;
        
        const count = this.messageInput.value.length;
        this.charCount.textContent = count;
        
        if (count > 900) {
            this.charCount.className = 'text-danger';
        } else if (count > 800) {
            this.charCount.className = 'text-warning';
        } else {
            this.charCount.className = 'text-muted';
        }
    }
    
    async handleFormSubmit(e) {
        e.preventDefault();
        
        const message = this.messageInput?.value.trim();
        if (!message || this.isTyping) return;
        
        // Add user message
        this.addMessage(message, 'user');
        
        // Clear input and reset height
        if (this.messageInput) {
            this.messageInput.value = '';
            this.messageInput.style.height = 'auto';
        }
        this.updateCharCount();
        
        // Show typing indicator
        this.showTyping();
        
        try {
            const response = await this.sendMessage(message);
            this.hideTyping();
            this.addMessage(response.response, 'bot');
        } catch (error) {
            this.hideTyping();
            const errorMsg = navigator.onLine ? 
                'Sorry, I\'m having trouble connecting right now. Please try again in a moment.' :
                'You\'re currently offline. Please check your connection and try again.';
            this.addMessage(errorMsg, 'bot', true);
            console.error('Chat error:', error);
        }
    }
    
    async sendMessage(message) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
        
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.sessionId
                }),
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
            
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                throw new Error('Request timed out');
            }
            throw error;
        }
    }
    
    addMessage(content, sender, isError = false) {
        if (!this.chatMessages || !this.typingIndicator) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message ${isError ? 'error-message' : ''}`;
        
        const timestamp = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        
        messageDiv.innerHTML = `
            <div class="message-avatar">
                <i class="bi bi-${sender === 'user' ? 'person-circle' : 'robot'}"></i>
            </div>
            <div class="message-content">
                <div class="message-bubble">
                    ${this.formatMessageContent(content)}
                </div>
                <div class="message-time">
                    <small class="text-muted">${timestamp}</small>
                </div>
            </div>
        `;
        
        // Insert before typing indicator
        this.chatMessages.insertBefore(messageDiv, this.typingIndicator);
        
        // Add to history
        this.chatHistory.push({
            content: content,
            sender: sender,
            timestamp: new Date().toISOString(),
            isError: isError
        });
        
        // Save to localStorage
        this.saveChatHistory();
        
        // Scroll to bottom
        this.scrollToBottom();
    }
    
    formatMessageContent(content) {
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>')
            .replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');
    }
    
    showTyping() {
        this.isTyping = true;
        if (this.typingIndicator) {
            this.typingIndicator.style.display = 'block';
        }
        if (this.sendButton) {
            this.sendButton.disabled = true;
        }
        this.scrollToBottom();
    }
    
    hideTyping() {
        this.isTyping = false;
        if (this.typingIndicator) {
            this.typingIndicator.style.display = 'none';
        }
        if (this.sendButton) {
            this.sendButton.disabled = false;
        }
    }
    
    scrollToBottom() {
        setTimeout(() => {
            if (this.chatMessages) {
                this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
            }
        }, 100);
    }
    
    clearChat() {
        if (!confirm('Are you sure you want to clear the chat history?')) {
            return;
        }
        
        this.chatHistory = [];
        
        if (this.chatMessages) {
            this.chatMessages.innerHTML = `
                <!-- Welcome Message -->
                <div class="message bot-message">
                    <div class="message-avatar">
                        <i class="bi bi-robot"></i>
                    </div>
                    <div class="message-content">
                        <div class="message-bubble">
                            <p class="mb-0">Chat cleared! How can I help you today?</p>
                        </div>
                        <div class="message-time">
                            <small class="text-muted">Just now</small>
                        </div>
                    </div>
                </div>

                <!-- Typing Indicator -->
                <div id="typing-indicator" class="message bot-message typing-indicator">
                    <div class="message-avatar">
                        <i class="bi bi-robot"></i>
                    </div>
                    <div class="message-content">
                        <div class="message-bubble">
                            <div class="typing-animation">
                                <span></span>
                                <span></span>
                                <span></span>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // Re-get the typing indicator reference
        this.typingIndicator = document.getElementById('typing-indicator');
        
        this.saveChatHistory();
        this.showToast('Chat history cleared', 'success');
    }
    
    downloadChat() {
        if (this.chatHistory.length === 0) {
            this.showToast('No chat history to download', 'info');
            return;
        }
        
        const chatText = this.chatHistory.map(msg => 
            `[${new Date(msg.timestamp).toLocaleString()}] ${msg.sender.toUpperCase()}: ${msg.content}`
        ).join('\n\n');
        
        const blob = new Blob([chatText], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `banking-chat-${new Date().toISOString().split('T')[0]}.txt`;
        
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        this.showToast('Chat downloaded successfully', 'success');
    }
    
    getSessionId() {
        let sessionId = localStorage.getItem('chat_session_id');
        if (!sessionId) {
            sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('chat_session_id', sessionId);
        }
        return sessionId;
    }
    
    saveChatHistory() {
        try {
            localStorage.setItem('chat_history', JSON.stringify(this.chatHistory));
        } catch (error) {
            console.warn('Could not save chat history to localStorage:', error);
        }
    }
    
    loadChatHistory() {
        try {
            const saved = localStorage.getItem('chat_history');
            if (saved) {
                this.chatHistory = JSON.parse(saved);
                
                // Restore messages (excluding the welcome message)
                this.chatHistory.forEach(msg => {
                    if (msg.content && msg.sender) {
                        this.addMessageToDOM(msg.content, msg.sender, msg.isError, msg.timestamp);
                    }
                });
            }
        } catch (error) {
            console.warn('Could not load chat history from localStorage:', error);
            this.chatHistory = [];
        }
    }
    
    addMessageToDOM(content, sender, isError = false, timestamp = null) {
        if (!this.chatMessages || !this.typingIndicator) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message ${isError ? 'error-message' : ''}`;
        
        const timeString = timestamp ? 
            new Date(timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) :
            new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        
        messageDiv.innerHTML = `
            <div class="message-avatar">
                <i class="bi bi-${sender === 'user' ? 'person-circle' : 'robot'}"></i>
            </div>
            <div class="message-content">
                <div class="message-bubble">
                    ${this.formatMessageContent(content)}
                </div>
                <div class="message-time">
                    <small class="text-muted">${timeString}</small>
                </div>
            </div>
        `;
        
        // Insert before typing indicator
        this.chatMessages.insertBefore(messageDiv, this.typingIndicator);
    }
    
    showToast(message, type = 'info') {
        // Create toast container if it doesn't exist
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'position-fixed top-0 end-0 p-3';
            toastContainer.style.zIndex = '9999';
            document.body.appendChild(toastContainer);
        }
        
        // Create toast
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info'} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        
        // Initialize and show toast
        const bsToast = new bootstrap.Toast(toast, {
            autohide: true,
            delay: 3000
        });
        bsToast.show();
        
        // Clean up after toast is hidden
        toast.addEventListener('hidden.bs.toast', () => {
            toastContainer.removeChild(toast);
        });
    }
}

// Global chat instance
let chatInterface;

// Initialize chat interface when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('chat-messages')) {
        chatInterface = new BankingChatInterface();
    }
});

// Global functions for buttons
function clearChat() {
    if (chatInterface) {
        chatInterface.clearChat();
    }
}

function downloadChat() {
    if (chatInterface) {
        chatInterface.downloadChat();
    }
}