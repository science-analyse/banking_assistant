// Banking Assistant - Enhanced Frontend JavaScript with PWA Features

class BankingAssistant {
    constructor() {
        this.isLoading = false;
        this.chatMessages = [];
        this.deferredPrompt = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.showWelcomeMessage();
        this.setupQuickActions();
        this.setupPWA();
        this.checkConnectivity();
        this.animateUI();
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

        // Clear chat
        const clearChat = document.getElementById('clear-chat');
        if (clearChat) {
            clearChat.addEventListener('click', () => {
                this.clearChat();
            });
        }

        // Share app
        const shareButton = document.getElementById('share-app');
        if (shareButton) {
            shareButton.addEventListener('click', () => {
                this.shareApp();
            });
        }

        // Install app
        const installButton = document.getElementById('install-app');
        if (installButton) {
            installButton.addEventListener('click', () => {
                this.installApp();
            });
        }
    }

    setupPWA() {
        // Handle install prompt
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            this.deferredPrompt = e;
            
            // Show install button
            const installButton = document.getElementById('install-app');
            if (installButton) {
                installButton.style.display = 'flex';
            }
        });

        // Handle app installed
        window.addEventListener('appinstalled', () => {
            console.log('PWA installed');
            this.deferredPrompt = null;
            
            // Hide install button
            const installButton = document.getElementById('install-app');
            if (installButton) {
                installButton.style.display = 'none';
            }
        });

        // Check if app is installed
        if (window.matchMedia('(display-mode: standalone)').matches) {
            console.log('App is running in standalone mode');
        }
    }

    async installApp() {
        if (!this.deferredPrompt) {
            return;
        }

        // Show install prompt
        this.deferredPrompt.prompt();

        // Wait for user choice
        const { outcome } = await this.deferredPrompt.userChoice;
        console.log(`User response to install prompt: ${outcome}`);

        // Clear the deferred prompt
        this.deferredPrompt = null;
    }

    async shareApp() {
        const shareData = {
            title: 'AI Banking Assistant',
            text: 'Check out this AI-powered banking assistant for all your financial needs!',
            url: window.location.href
        };

        try {
            if (navigator.share) {
                await navigator.share(shareData);
                console.log('Shared successfully');
            } else {
                // Fallback to copying URL
                await navigator.clipboard.writeText(window.location.href);
                this.showNotification('Link copied to clipboard!');
            }
        } catch (error) {
            console.error('Error sharing:', error);
        }
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
            'account-types': 'What types of bank accounts are available and which one should I choose?',
            'loans': 'Tell me about different loan options and their requirements',
            'savings': 'What are the best savings and deposit options available?',
            'digital-banking': 'How can I use digital banking services effectively?',
            'security': 'What security measures should I follow for safe banking?',
            'help': 'I need help understanding banking terms and procedures'
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
            content: `Welcome to your AI Banking Assistant! 🏦✨

I'm here to help you navigate the world of banking with confidence. I can assist you with:

• **Account Types** - Find the perfect account for your needs
• **Loans & Credit** - Understand your borrowing options
• **Savings & Investments** - Grow your wealth wisely
• **Digital Banking** - Master online and mobile banking
• **Security Tips** - Keep your finances safe
• **Financial Education** - Learn banking basics and beyond

Feel free to ask me anything about banking! I'm here to provide clear, helpful guidance for all your financial questions.

*How can I help you today?*`,
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

            // Vibrate on response (if supported)
            if ('vibrate' in navigator && document.hidden === false) {
                navigator.vibrate(50);
            }

        } catch (error) {
            console.error('Error sending message:', error);
            
            // Remove typing indicator
            this.removeTypingIndicator();
            
            // Show error message
            this.addMessageToChat({
                role: 'assistant',
                content: 'Sorry, I encountered an error. Please check your connection and try again.',
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
        
        // Enhanced auto-scroll with proper timing
        this.scrollToBottom(true);
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
        
        // Scroll to show typing indicator
        this.scrollToBottom(true);
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

    // Enhanced scroll function with better behavior
    scrollToBottom(smooth = false) {
        // Use a small delay to ensure DOM has updated
        setTimeout(() => {
            const chatContainer = document.querySelector('.chat-container');
            const chatMessages = document.getElementById('chat-messages');
            
            if (chatMessages && chatContainer) {
                // Get the height of the messages container
                const scrollHeight = chatMessages.scrollHeight;
                
                // Scroll the window instead of just the chat container
                const containerRect = chatContainer.getBoundingClientRect();
                const targetScrollY = window.scrollY + containerRect.bottom - window.innerHeight + 100;
                
                if (smooth) {
                    // Smooth scroll behavior
                    window.scrollTo({
                        top: Math.max(0, targetScrollY),
                        behavior: 'smooth'
                    });
                } else {
                    // Instant scroll
                    window.scrollTo(0, Math.max(0, targetScrollY));
                }
                
                // Also scroll the messages container if it has its own scroll
                chatMessages.scrollTo({
                    top: scrollHeight,
                    behavior: smooth ? 'smooth' : 'auto'
                });
            }
        }, 50);
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
                
                // Show notification
                this.showNotification('Chat cleared successfully');
                
                // Scroll to top after clearing
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        } catch (error) {
            console.error('Error clearing chat:', error);
        }
    }

    showNotification(message) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = 'notification';
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            bottom: 100px;
            left: 50%;
            transform: translateX(-50%);
            background: var(--gradient-primary);
            color: white;
            padding: 0.75rem 1.5rem;
            border-radius: var(--radius-full);
            box-shadow: var(--shadow-lg);
            z-index: 1000;
            animation: slideUp 0.3s ease-out;
        `;

        document.body.appendChild(notification);

        // Remove after 3 seconds
        setTimeout(() => {
            notification.style.animation = 'slideDown 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    checkConnectivity() {
        // Update connection status
        this.updateConnectionStatus(navigator.onLine);

        // Listen for connection changes
        window.addEventListener('online', () => {
            this.updateConnectionStatus(true);
            this.showNotification('Connection restored');
        });

        window.addEventListener('offline', () => {
            this.updateConnectionStatus(false);
            this.showNotification('You are offline');
        });
    }

    updateConnectionStatus(isOnline) {
        const statusDot = document.querySelector('.status-dot');
        const statusText = document.querySelector('.connection-status span:last-child');
        
        if (statusDot && statusText) {
            if (isOnline) {
                statusDot.classList.add('connected');
                statusText.textContent = 'Connected';
            } else {
                statusDot.classList.remove('connected');
                statusText.textContent = 'Offline';
            }
        }
    }

    animateUI() {
        // Add subtle animations on load
        const elements = document.querySelectorAll('.quick-action-btn, .message');
        elements.forEach((el, index) => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(20px)';
            setTimeout(() => {
                el.style.transition = 'all 0.3s ease-out';
                el.style.opacity = '1';
                el.style.transform = 'translateY(0)';
            }, index * 50);
        });
    }
}

// Add custom styles for notifications
const style = document.createElement('style');
style.textContent = `
    @keyframes slideUp {
        from {
            transform: translate(-50%, 100%);
            opacity: 0;
        }
        to {
            transform: translate(-50%, 0);
            opacity: 1;
        }
    }
    
    @keyframes slideDown {
        from {
            transform: translate(-50%, 0);
            opacity: 1;
        }
        to {
            transform: translate(-50%, 100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const app = new BankingAssistant();
    
    // Register service worker for PWA functionality
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/static/sw.js')
            .then(registration => {
                console.log('Service Worker registered successfully');
                
                // Check for updates periodically
                setInterval(() => {
                    registration.update();
                }, 60000); // Check every minute
            })
            .catch(error => {
                console.log('Service Worker registration failed:', error);
            });
    }
    
    // Handle page visibility changes
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) {
            // Page is visible again
            app.checkConnectivity();
        }
    });
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + K to focus input
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const messageInput = document.getElementById('message-input');
            if (messageInput) {
                messageInput.focus();
            }
        }
        
        // Ctrl/Cmd + L to clear chat
        if ((e.ctrlKey || e.metaKey) && e.key === 'l') {
            e.preventDefault();
            app.clearChat();
        }
    });
    
    // Enhanced scroll behavior for mobile
    let isScrolling = false;
    window.addEventListener('scroll', () => {
        if (!isScrolling) {
            window.requestAnimationFrame(() => {
                // Add any scroll-based logic here if needed
                isScrolling = false;
            });
            isScrolling = true;
        }
    });
});