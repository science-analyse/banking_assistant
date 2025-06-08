// Banking Assistant for Azerbaijan - Frontend JavaScript

class BankingAssistant {
    constructor() {
        this.isLoading = false;
        this.chatMessages = [];
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupTheme();
        this.showWelcomeMessage();
        this.setupQuickActions();
    }

    setupEventListeners() {
        // Chat form submission
        const chatForm = document.getElementById('chat-form');
        const messageInput = document.getElementById('message-input');
        const sendButton = document.getElementById('send-button');

        if (chatForm) {
            chatForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.sendMessage();
            });
        }

        // Send button click
        if (sendButton) {
            sendButton.addEventListener('click', () => {
                this.sendMessage();
            });
        }

        // Auto-resize textarea
        if (messageInput) {
            messageInput.addEventListener('input', () => {
                this.autoResizeTextarea(messageInput);
            });

            // Send on Enter (but not Shift+Enter)
            messageInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }

        // Theme toggle
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                this.toggleTheme();
            });
        }

        // Clear chat
        const clearChat = document.getElementById('clear-chat');
        if (clearChat) {
            clearChat.addEventListener('click', () => {
                this.clearChat();
            });
        }
    }

    setupTheme() {
        // Load saved theme or default to light
        const savedTheme = localStorage.getItem('banking-assistant-theme') || 'light';
        this.setTheme(savedTheme);
    }

    setTheme(theme) {
        document.body.classList.toggle('dark', theme === 'dark');
        
        // Update theme toggle icons
        const sunIcon = document.querySelector('.sun-icon');
        const moonIcon = document.querySelector('.moon-icon');
        
        if (sunIcon && moonIcon) {
            if (theme === 'dark') {
                sunIcon.style.display = 'block';
                moonIcon.style.display = 'none';
            } else {
                sunIcon.style.display = 'none';
                moonIcon.style.display = 'block';
            }
        }
        
        localStorage.setItem('banking-assistant-theme', theme);
    }

    toggleTheme() {
        const currentTheme = document.body.classList.contains('dark') ? 'dark' : 'light';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        this.setTheme(newTheme);
    }

    setupQuickActions() {
        const quickActionBtns = document.querySelectorAll('.quick-action-btn');
        quickActionBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                this.handleQuickAction(action);
            });
        });
    }

    handleQuickAction(action) {
        const messages = {
            'find-atm': 'Where can I find the nearest ATM in Baku?',
            'currency-rates': 'What are the current USD to AZN exchange rates?',
            'open-account': 'How can I open a bank account in Azerbaijan?',
            'loans': 'Tell me about loan options available in Azerbaijani banks',
            'cards': 'What types of bank cards are available?',
            'branches': 'Show me bank branches in Baku'
        };

        const message = messages[action];
        if (message) {
            this.sendPredefinedMessage(message);
        }
    }

    sendPredefinedMessage(message) {
        const messageInput = document.getElementById('message-input');
        if (messageInput) {
            messageInput.value = message;
            this.sendMessage();
        }
    }

    showWelcomeMessage() {
        const welcomeMessage = {
            role: 'assistant',
            content: `Salam! Welcome to the Azerbaijan Banking Assistant! 👋

I'm here to help you with:
• Finding bank branches and ATMs in Azerbaijan
• Information about banking services and products  
• Currency exchange rates and information
• Account opening procedures
• Loan and deposit options
• General banking advice

Feel free to ask me anything about banking in Azerbaijan in either English or Azerbaijani!

*Azərbaycan bankçılıq xidmətləri haqqında hər hansı sualınız varsa, mənə müraciət edin!*`,
            timestamp: new Date().toISOString(),
            isWelcome: true
        };

        this.addMessageToChat(welcomeMessage);
    }

    autoResizeTextarea(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }

    async sendMessage() {
        const messageInput = document.getElementById('message-input');
        const message = messageInput?.value.trim();

        if (!message || this.isLoading) return;

        // Clear input and reset height
        messageInput.value = '';
        messageInput.style.height = 'auto';

        // Add user message to chat
        this.addMessageToChat({
            role: 'user',
            content: message,
            timestamp: new Date().toISOString()
        });

        // Show typing indicator
        this.showTypingIndicator();

        try {
            this.isLoading = true;
            this.updateSendButton(false);

            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            // Remove typing indicator
            this.removeTypingIndicator();

            // Add assistant response
            this.addMessageToChat({
                role: 'assistant',
                content: data.response,
                timestamp: data.timestamp
            });

        } catch (error) {
            console.error('Error sending message:', error);
            
            // Remove typing indicator
            this.removeTypingIndicator();
            
            // Show error message
            this.addMessageToChat({
                role: 'assistant',
                content: 'Sorry, I encountered an error. Please try again.',
                timestamp: new Date().toISOString(),
                isError: true
            });
        } finally {
            this.isLoading = false;
            this.updateSendButton(true);
        }
    }

    addMessageToChat(message) {
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) return;

        const messageElement = this.createMessageElement(message);
        chatMessages.appendChild(messageElement);
        
        // Scroll to bottom
        this.scrollToBottom();
    }

    createMessageElement(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${message.role}${message.isWelcome ? ' welcome-message' : ''}${message.isError ? ' error' : ''}`;

        const avatar = this.createAvatar(message.role);
        const content = this.createMessageContent(message);

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);

        return messageDiv;
    }

    createAvatar(role) {
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        
        if (role === 'user') {
            avatar.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
            `;
        } else {
            avatar.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
            `;
        }
        
        return avatar;
    }

    createMessageContent(message) {
        const content = document.createElement('div');
        content.className = 'message-content';
        
        // Process message content for formatting
        const formattedContent = this.formatMessageContent(message.content);
        content.innerHTML = formattedContent;
        
        return content;
    }

    formatMessageContent(content) {
        // Convert markdown-like formatting to HTML
        let formatted = content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');

        // Convert bullet points
        formatted = formatted.replace(/^[•·-]\s(.+)$/gm, '<li>$1</li>');
        
        // Wrap consecutive list items in ul tags
        formatted = formatted.replace(/(<li>.*<\/li>)+/gs, '<ul>$&</ul>');
        
        return formatted;
    }

    showTypingIndicator() {
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) return;

        const typingDiv = document.createElement('div');
        typingDiv.className = 'message assistant typing';
        typingDiv.id = 'typing-indicator';

        const avatar = this.createAvatar('assistant');
        const content = document.createElement('div');
        content.className = 'message-content';
        content.innerHTML = `
            <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;

        typingDiv.appendChild(avatar);
        typingDiv.appendChild(content);
        chatMessages.appendChild(typingDiv);
        
        this.scrollToBottom();
    }

    removeTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    updateSendButton(enabled) {
        const sendButton = document.getElementById('send-button');
        if (sendButton) {
            sendButton.disabled = !enabled;
            sendButton.style.opacity = enabled ? '1' : '0.6';
        }
    }

    scrollToBottom() {
        const chatMessages = document.getElementById('chat-messages');
        if (chatMessages) {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }

    async clearChat() {
        try {
            const response = await fetch('/api/clear-chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (response.ok) {
                // Clear chat messages from UI
                const chatMessages = document.getElementById('chat-messages');
                if (chatMessages) {
                    chatMessages.innerHTML = '';
                }
                
                // Show welcome message again
                this.showWelcomeMessage();
            }
        } catch (error) {
            console.error('Error clearing chat:', error);
        }
    }
}

// Connection status
class ConnectionStatus {
    constructor() {
        this.isOnline = navigator.onLine;
        this.init();
    }

    init() {
        this.updateStatus();
        
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.updateStatus();
        });

        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.updateStatus();
        });
    }

    updateStatus() {
        const statusDot = document.querySelector('.status-dot');
        const statusText = document.querySelector('.connection-status span:last-child');
        
        if (statusDot && statusText) {
            if (this.isOnline) {
                statusDot.classList.add('connected');
                statusText.textContent = 'Connected';
            } else {
                statusDot.classList.remove('connected');
                statusText.textContent = 'Offline';
            }
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const app = new BankingAssistant();
    const connectionStatus = new ConnectionStatus();
    
    // Register service worker for PWA functionality
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/static/sw.js')
            .then(registration => {
                console.log('Service Worker registered successfully');
            })
            .catch(error => {
                console.log('Service Worker registration failed');
            });
    }
});