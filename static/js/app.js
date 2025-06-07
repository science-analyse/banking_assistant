// Banking AI Assistant - Chat Only Version
// Enhanced mobile-first, lightweight JavaScript

class BankingAssistant {
    constructor() {
        this.isOnline = navigator.onLine;
        this.chatHistory = [];
        this.sessionId = this.getSessionId();
        this.isTyping = false;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.initializeConnectionMonitoring();
        this.loadChatHistory();
        
        // Initialize page when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initializePage());
        } else {
            this.initializePage();
        }
    }
    
    initializePage() {
        this.updateConnectionStatus();
        this.initializeChatInterface();
        
        // Set update time in footer
        const updateTimeEl = document.getElementById('update-time');
        if (updateTimeEl) {
            updateTimeEl.textContent = new Date().toLocaleString();
        }
    }
    
    setupEventListeners() {
        // Connection status monitoring
        window.addEventListener('online', () => this.handleConnectionChange(true));
        window.addEventListener('offline', () => this.handleConnectionChange(false));
        
        // Mobile viewport handling
        window.addEventListener('resize', this.debounce(() => this.handleResize(), 250));
        
        // Visibility change handling
        document.addEventListener('visibilitychange', () => this.handleVisibilityChange());
        
        // Error handling
        window.addEventListener('error', (e) => this.handleGlobalError(e));
        window.addEventListener('unhandledrejection', (e) => this.handlePromiseRejection(e));
    }
    
    initializeConnectionMonitoring() {
        // Ping server periodically to check connection
        setInterval(() => this.checkServerConnection(), 30000); // Every 30 seconds
    }
    
    async checkServerConnection() {
        if (!this.isOnline) return;
        
        try {
            const response = await fetch('/api/health', {
                method: 'GET',
                cache: 'no-cache',
                signal: AbortSignal.timeout(5000)
            });
            
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}`);
            }
            
            const data = await response.json();
            this.updateServerStatus(data);
            
        } catch (error) {
            console.warn('Server connection check failed:', error);
            this.handleServerConnectionError();
        }
    }
    
    updateServerStatus(healthData) {
        // Update UI based on server health status
        const statusEl = document.getElementById('connection-status');
        if (statusEl && healthData.status === 'healthy') {
            statusEl.innerHTML = '<i class="bi bi-wifi"></i> Online';
            statusEl.className = 'badge bg-success ms-2';
        }
    }
    
    handleServerConnectionError() {
        const statusEl = document.getElementById('connection-status');
        if (statusEl) {
            statusEl.innerHTML = '<i class="bi bi-exclamation-triangle"></i> Issues';
            statusEl.className = 'badge bg-warning ms-2';
        }
    }
    
    handleConnectionChange(isOnline) {
        this.isOnline = isOnline;
        this.updateConnectionStatus();
        
        if (isOnline) {
            this.showToast('Connection restored', 'success');
            this.checkServerConnection();
        } else {
            this.showToast('Connection lost - working offline', 'warning');
        }
    }
    
    updateConnectionStatus() {
        const statusEl = document.getElementById('connection-status');
        if (!statusEl) return;
        
        if (this.isOnline) {
            statusEl.innerHTML = '<i class="bi bi-wifi"></i> Online';
            statusEl.className = 'badge bg-success ms-2';
        } else {
            statusEl.innerHTML = '<i class="bi bi-wifi-off"></i> Offline';
            statusEl.className = 'badge bg-danger ms-2';
        }
    }
    
    handleResize() {
        // Handle mobile orientation changes and resize
        this.adjustChatContainerHeight();
        this.scrollToBottom();
    }
    
    adjustChatContainerHeight() {
        const chatContainer = document.querySelector('.chat-container');
        const chatMessages = document.querySelector('.chat-messages');
        
        if (chatContainer && window.innerWidth <= 767) {
            // Mobile-specific height adjustments
            const viewportHeight = window.innerHeight;
            const navbarHeight = 60;
            const welcomeHeight = document.querySelector('.welcome-section')?.offsetHeight || 0;
            const quickActionsHeight = document.querySelector('.quick-actions')?.offsetHeight || 0;
            const headerHeight = 70;
            const inputHeight = 120;
            
            const availableHeight = viewportHeight - navbarHeight - welcomeHeight - quickActionsHeight - 40; // 40px for margins
            const messagesHeight = availableHeight - headerHeight - inputHeight;
            
            chatContainer.style.height = `${availableHeight}px`;
            if (chatMessages) {
                chatMessages.style.height = `${messagesHeight}px`;
            }
        }
    }
    
    handleVisibilityChange() {
        if (document.visibilityState === 'visible') {
            // Page became visible, check connection
            this.checkServerConnection();
        }
    }
    
    handleGlobalError(error) {
        console.error('Global error:', error);
        this.showToast('An unexpected error occurred', 'error');
    }
    
    handlePromiseRejection(event) {
        console.error('Unhandled promise rejection:', event.reason);
        this.showToast('A background operation failed', 'error');
    }
    
    // Chat interface initialization
    initializeChatInterface() {
        const chatForm = document.getElementById('chat-form');
        const messageInput = document.getElementById('message-input');
        const charCount = document.getElementById('char-count');
        
        if (!chatForm || !messageInput) return;
        
        // Form submission
        chatForm.addEventListener('submit', (e) => this.handleFormSubmit(e));
        
        // Input handling
        messageInput.addEventListener('input', () => {
            this.autoResizeTextarea(messageInput);
            this.updateCharCount();
        });
        
        // Enter key handling
        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleFormSubmit(e);
            }
        });
        
        // Auto-focus on mobile (with delay to avoid keyboard issues)
        if (window.innerWidth > 767) {
            setTimeout(() => messageInput.focus(), 500);
        }
        
        // Adjust chat height after initialization
        setTimeout(() => this.adjustChatContainerHeight(), 100);
    }
    
    async handleFormSubmit(e) {
        e.preventDefault();
        
        const messageInput = document.getElementById('message-input');
        const message = messageInput.value.trim();
        
        if (!message || this.isTyping || message.length > 1000) return;
        
        // Add user message
        this.addMessage(message, 'user');
        
        // Clear input and reset height
        messageInput.value = '';
        messageInput.style.height = 'auto';
        this.updateCharCount();
        
        // Show typing indicator
        this.showTyping();
        
        try {
            const response = await this.sendMessage(message);
            this.hideTyping();
            this.addMessage(response.response, 'bot');
        } catch (error) {
            this.hideTyping();
            const errorMsg = this.isOnline ? 
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
        const chatMessages = document.getElementById('chat-messages');
        const typingIndicator = document.getElementById('typing-indicator');
        
        if (!chatMessages) return;
        
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
        if (typingIndicator) {
            chatMessages.insertBefore(messageDiv, typingIndicator);
        } else {
            chatMessages.appendChild(messageDiv);
        }
        
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
            .replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
    }
    
    showTyping() {
        this.isTyping = true;
        const typingIndicator = document.getElementById('typing-indicator');
        const sendButton = document.getElementById('send-button');
        
        if (typingIndicator) typingIndicator.style.display = 'block';
        if (sendButton) sendButton.disabled = true;
        
        this.scrollToBottom();
    }
    
    hideTyping() {
        this.isTyping = false;
        const typingIndicator = document.getElementById('typing-indicator');
        const sendButton = document.getElementById('send-button');
        
        if (typingIndicator) typingIndicator.style.display = 'none';
        if (sendButton) sendButton.disabled = false;
    }
    
    scrollToBottom() {
        const chatMessages = document.getElementById('chat-messages');
        if (chatMessages) {
            setTimeout(() => {
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }, 100);
        }
    }
    
    autoResizeTextarea(textarea) {
        if (!textarea) return;
        
        textarea.style.height = 'auto';
        const newHeight = Math.min(textarea.scrollHeight, 120);
        textarea.style.height = newHeight + 'px';
    }
    
    updateCharCount() {
        const messageInput = document.getElementById('message-input');
        const charCount = document.getElementById('char-count');
        
        if (!messageInput || !charCount) return;
        
        const count = messageInput.value.length;
        charCount.textContent = count;
        
        if (count > 900) {
            charCount.className = 'text-danger';
        } else if (count > 800) {
            charCount.className = 'text-warning';
        } else {
            charCount.className = 'text-muted';
        }
    }
    
    // Quick message functions
    sendQuickMessage(message) {
        const messageInput = document.getElementById('message-input');
        if (messageInput) {
            messageInput.value = message;
            this.handleFormSubmit(new Event('submit'));
        }
    }
    
    // Chat management
    clearChat() {
        if (!confirm('Are you sure you want to clear the chat history?')) return;
        
        this.chatHistory = [];
        const chatMessages = document.getElementById('chat-messages');
        
        if (chatMessages) {
            chatMessages.innerHTML = `
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
            `;
        }
        
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
        
        // Handle mobile download
        if (navigator.share && /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
            navigator.share({
                title: 'Banking Chat History',
                text: chatText
            }).catch(() => {
                // Fallback to regular download
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            });
        } else {
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }
        
        URL.revokeObjectURL(url);
        this.showToast('Chat history downloaded', 'success');
    }
    
    // Session management
    getSessionId() {
        let sessionId = localStorage.getItem('chat_session_id');
        if (!sessionId) {
            sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('chat_session_id', sessionId);
        }
        return sessionId;
    }
    
    // Chat history persistence
    saveChatHistory() {
        try {
            // Limit history to last 100 messages to prevent storage issues
            const limitedHistory = this.chatHistory.slice(-100);
            localStorage.setItem('chat_history', JSON.stringify(limitedHistory));
            this.chatHistory = limitedHistory;
        } catch (e) {
            console.warn('Could not save chat history:', e);
            // Clear old data and try again
            localStorage.removeItem('chat_history');
        }
    }
    
    loadChatHistory() {
        try {
            const saved = localStorage.getItem('chat_history');
            if (saved) {
                this.chatHistory = JSON.parse(saved);
                
                // Restore messages after DOM is ready
                setTimeout(() => {
                    this.restoreChatMessages();
                }, 100);
            }
        } catch (e) {
            console.warn('Could not load chat history:', e);
            localStorage.removeItem('chat_history');
            this.chatHistory = [];
        }
    }
    
    restoreChatMessages() {
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages || this.chatHistory.length === 0) return;
        
        // Clear existing messages except welcome
        const welcomeMessage = chatMessages.querySelector('.message.bot-message');
        chatMessages.innerHTML = '';
        if (welcomeMessage) {
            chatMessages.appendChild(welcomeMessage);
        }
        
        // Restore chat history
        this.chatHistory.forEach(msg => {
            if (msg.content && msg.sender) {
                this.addMessageToDOM(msg.content, msg.sender, msg.isError || false, msg.timestamp);
            }
        });
        
        this.scrollToBottom();
    }
    
    addMessageToDOM(content, sender, isError = false, timestamp = null) {
        const chatMessages = document.getElementById('chat-messages');
        const typingIndicator = document.getElementById('typing-indicator');
        
        if (!chatMessages) return;
        
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
        
        if (typingIndicator) {
            chatMessages.insertBefore(messageDiv, typingIndicator);
        } else {
            chatMessages.appendChild(messageDiv);
        }
    }
    
    // Toast notification system
    showToast(message, type = 'info') {
        const toastContainer = document.getElementById('toast-container');
        if (!toastContainer) return;
        
        const toastId = 'toast-' + Date.now();
        const bgClass = type === 'error' ? 'bg-danger' : type === 'success' ? 'bg-success' : 'bg-info';
        
        const toastHTML = `
            <div id="${toastId}" class="toast ${bgClass} text-white" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="toast-body">
                    ${message}
                    <button type="button" class="btn-close btn-close-white float-end" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        `;
        
        toastContainer.insertAdjacentHTML('beforeend', toastHTML);
        
        const toastElement = document.getElementById(toastId);
        if (toastElement && typeof bootstrap !== 'undefined') {
            const toast = new bootstrap.Toast(toastElement);
            toast.show();
            
            // Remove toast element after it's hidden
            toastElement.addEventListener('hidden.bs.toast', function() {
                this.remove();
            });
        }
    }
    
    // Utility function for debouncing
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// Global functions for template compatibility
window.sendQuickMessage = function(message) {
    if (window.bankingAssistant) {
        window.bankingAssistant.sendQuickMessage(message);
    }
};

window.clearChat = function() {
    if (window.bankingAssistant) {
        window.bankingAssistant.clearChat();
    }
};

window.downloadChat = function() {
    if (window.bankingAssistant) {
        window.bankingAssistant.downloadChat();
    }
};

window.showToast = function(message, type = 'info') {
    if (window.bankingAssistant) {
        window.bankingAssistant.showToast(message, type);
    }
};

// Initialize the application
window.bankingAssistant = new BankingAssistant();