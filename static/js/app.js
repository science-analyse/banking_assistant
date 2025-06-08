// Banking AI Assistant - Frontend JavaScript
(function() {
    'use strict';

    // DOM Elements
    const elements = {
        chatForm: document.getElementById('chatForm'),
        messageInput: document.getElementById('messageInput'),
        sendButton: document.getElementById('sendButton'),
        chatMessages: document.getElementById('chatMessages'),
        connectionStatus: document.getElementById('connectionStatus'),
        themeToggle: document.getElementById('themeToggle'),
        menuToggle: document.getElementById('menuToggle'),
        loadingOverlay: document.getElementById('loadingOverlay')
    };

    // Application State
    const state = {
        websocket: null,
        isConnected: false,
        messageHistory: [],
        reconnectAttempts: 0,
        maxReconnectAttempts: 5,
        reconnectDelay: 1000,
        isTyping: false
    };

    // Initialize Application
    function init() {
        setupEventListeners();
        setupWebSocket();
        loadTheme();
        setupServiceWorker();
        focusInput();
        
        // Prevent body scroll on mobile
        document.body.addEventListener('touchmove', function(e) {
            if (!e.target.closest('.chat-messages') && !e.target.closest('.quick-actions-content')) {
                e.preventDefault();
            }
        }, { passive: false });
    }

    // Event Listeners
    function setupEventListeners() {
        // Chat form submission
        elements.chatForm.addEventListener('submit', handleFormSubmit);
        
        // Theme toggle
        elements.themeToggle.addEventListener('click', toggleTheme);
        
        // Menu toggle (for mobile)
        elements.menuToggle.addEventListener('click', toggleMenu);
        
        // Auto-resize input
        elements.messageInput.addEventListener('input', handleInputResize);
        
        // Handle Enter key
        elements.messageInput.addEventListener('keydown', handleKeyDown);
    }

    // WebSocket Setup
    function setupWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        try {
            state.websocket = new WebSocket(wsUrl);
            
            state.websocket.onopen = handleWebSocketOpen;
            state.websocket.onmessage = handleWebSocketMessage;
            state.websocket.onclose = handleWebSocketClose;
            state.websocket.onerror = handleWebSocketError;
        } catch (error) {
            console.error('WebSocket creation failed:', error);
            fallbackToHTTP();
        }
    }

    // WebSocket Event Handlers
    function handleWebSocketOpen() {
        console.log('WebSocket connected');
        state.isConnected = true;
        state.reconnectAttempts = 0;
        updateConnectionStatus(true);
    }

    function handleWebSocketMessage(event) {
        try {
            const data = JSON.parse(event.data);
            displayMessage(data.response, 'assistant', data.data_sources);
            hideTypingIndicator();
        } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
        }
    }

    function handleWebSocketClose() {
        console.log('WebSocket disconnected');
        state.isConnected = false;
        updateConnectionStatus(false);
        attemptReconnect();
    }

    function handleWebSocketError(error) {
        console.error('WebSocket error:', error);
        fallbackToHTTP();
    }

    // Reconnection Logic
    function attemptReconnect() {
        if (state.reconnectAttempts < state.maxReconnectAttempts) {
            state.reconnectAttempts++;
            console.log(`Attempting to reconnect... (${state.reconnectAttempts}/${state.maxReconnectAttempts})`);
            
            setTimeout(() => {
                setupWebSocket();
            }, state.reconnectDelay * state.reconnectAttempts);
        } else {
            console.log('Max reconnection attempts reached. Falling back to HTTP.');
            fallbackToHTTP();
        }
    }

    // Form Submission Handler
    async function handleFormSubmit(event) {
        event.preventDefault();
        
        const message = elements.messageInput.value.trim();
        if (!message) return;
        
        // Display user message
        displayMessage(message, 'user');
        
        // Clear input
        elements.messageInput.value = '';
        handleInputResize();
        
        // Show typing indicator
        showTypingIndicator();
        
        // Send message
        if (state.isConnected && state.websocket.readyState === WebSocket.OPEN) {
            sendViaWebSocket(message);
        } else {
            await sendViaHTTP(message);
        }
    }

    // Send message via WebSocket
    function sendViaWebSocket(message) {
        try {
            state.websocket.send(JSON.stringify({
                message: message,
                context: state.messageHistory.slice(-5) // Send last 5 messages for context
            }));
        } catch (error) {
            console.error('Failed to send WebSocket message:', error);
            sendViaHTTP(message);
        }
    }

    // Send message via HTTP (fallback)
    async function sendViaHTTP(message) {
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    context: state.messageHistory.slice(-5)
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            displayMessage(data.response, 'assistant', data.data_sources);
            hideTypingIndicator();
        } catch (error) {
            console.error('Failed to send HTTP message:', error);
            displayError('Failed to send message. Please try again.');
            hideTypingIndicator();
        }
    }

    // Display Message in Chat
    function displayMessage(content, sender, dataSources = []) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        // Create avatar
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        avatarDiv.innerHTML = sender === 'user' ? getUserAvatar() : getAssistantAvatar();
        
        // Create content
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Process content (handle markdown, links, etc.)
        contentDiv.innerHTML = processMessageContent(content);
        
        // Add data sources if available
        if (dataSources && dataSources.length > 0) {
            const sourcesDiv = document.createElement('div');
            sourcesDiv.className = 'data-sources';
            sourcesDiv.innerHTML = `
                <span class="sources-label">Sources:</span>
                ${dataSources.map(source => `<span class="source-tag">${source}</span>`).join('')}
            `;
            contentDiv.appendChild(sourcesDiv);
        }
        
        // Assemble message
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);
        
        // Add to chat
        elements.chatMessages.appendChild(messageDiv);
        
        // Add to history
        state.messageHistory.push({ role: sender, content: content });
        
        // Scroll to bottom
        scrollToBottom();
    }

    // Display Error Message
    function displayError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'message error';
        errorDiv.innerHTML = `
            <div class="message-content">
                <p class="error-message">${message}</p>
            </div>
        `;
        elements.chatMessages.appendChild(errorDiv);
        scrollToBottom();
    }

    // Typing Indicator
    function showTypingIndicator() {
        if (state.isTyping) return;
        
        state.isTyping = true;
        const typingDiv = document.createElement('div');
        typingDiv.id = 'typingIndicator';
        typingDiv.className = 'message assistant typing';
        typingDiv.innerHTML = `
            <div class="message-avatar">${getAssistantAvatar()}</div>
            <div class="message-content">
                <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
        elements.chatMessages.appendChild(typingDiv);
        scrollToBottom();
    }

    function hideTypingIndicator() {
        state.isTyping = false;
        const typingIndicator = document.getElementById('typingIndicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    // Process Message Content
    function processMessageContent(content) {
        // Escape HTML
        content = escapeHtml(content);
        
        // Convert markdown-style formatting
        content = content
            // Bold
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            // Italic
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            // Code blocks
            .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
            // Inline code
            .replace(/`(.*?)`/g, '<code>$1</code>')
            // Links
            .replace(/\[([^\]]+)\]\(([^\)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
            // Line breaks
            .replace(/\n/g, '<br>');
        
        return content;
    }

    // Utility Functions
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function getUserAvatar() {
        return `
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="12" r="10" fill="currentColor" opacity="0.2"/>
                <path d="M12 12C14.21 12 16 10.21 16 8C16 5.79 14.21 4 12 4C9.79 4 8 5.79 8 8C8 10.21 9.79 12 12 12Z" fill="currentColor"/>
                <path d="M12 14C7.59 14 4 16.69 4 20V22H20V20C20 16.69 16.41 14 12 14Z" fill="currentColor"/>
            </svg>
        `;
    }

    function getAssistantAvatar() {
        return `
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2L2 7V12C2 16.5 4.23 20.68 7.62 23.15L12 24L16.38 23.15C19.77 20.68 22 16.5 22 12V7L12 2Z" fill="currentColor" opacity="0.2"/>
                <path d="M12 2L2 7V12C2 16.5 4.23 20.68 7.62 23.15L12 24L16.38 23.15C19.77 20.68 22 16.5 22 12V7L12 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M12 8V16M8 12H16" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
        `;
    }

    function scrollToBottom() {
        const messagesContainer = elements.chatMessages;
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        // Also ensure the page doesn't jump around
        window.scrollTo(0, 0);
    }

    function focusInput() {
        elements.messageInput.focus();
    }

    // Connection Status
    function updateConnectionStatus(isConnected) {
        const statusDot = elements.connectionStatus.querySelector('.status-dot');
        const statusText = elements.connectionStatus.querySelector('.status-text');
        
        if (isConnected) {
            statusDot.classList.add('connected');
            statusText.textContent = 'Connected';
        } else {
            statusDot.classList.remove('connected');
            statusText.textContent = 'Connecting...';
        }
    }

    // Theme Management
    function loadTheme() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.body.className = savedTheme;
        updateThemeIcon(savedTheme);
    }

    function toggleTheme() {
        const currentTheme = document.body.className;
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        
        document.body.className = newTheme;
        localStorage.setItem('theme', newTheme);
        updateThemeIcon(newTheme);
    }

    function updateThemeIcon(theme) {
        const sunIcon = elements.themeToggle.querySelector('.sun-icon');
        const moonIcon = elements.themeToggle.querySelector('.moon-icon');
        
        if (theme === 'dark') {
            sunIcon.style.display = 'block';
            moonIcon.style.display = 'none';
        } else {
            sunIcon.style.display = 'none';
            moonIcon.style.display = 'block';
        }
    }

    // Mobile Menu Toggle
    function toggleMenu() {
        document.body.classList.toggle('menu-open');
    }

    // Input Auto-resize
    function handleInputResize() {
        elements.messageInput.style.height = 'auto';
        elements.messageInput.style.height = Math.min(elements.messageInput.scrollHeight, 120) + 'px';
    }

    // Handle Enter Key
    function handleKeyDown(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            elements.chatForm.dispatchEvent(new Event('submit'));
        }
    }

    // Quick Message Function (called from HTML)
    window.sendQuickMessage = function(message) {
        elements.messageInput.value = message;
        elements.chatForm.dispatchEvent(new Event('submit'));
    };

    // Service Worker Setup
    function setupServiceWorker() {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/static/sw.js')
                .then(registration => console.log('ServiceWorker registered:', registration))
                .catch(error => console.log('ServiceWorker registration failed:', error));
        }
    }

    // Fallback to HTTP
    function fallbackToHTTP() {
        console.log('Using HTTP fallback for communication');
        state.isConnected = false;
        updateConnectionStatus(false);
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();