// Global variables
let conversationContext = [];
let isProcessing = false;

// DOM elements
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const chatForm = document.getElementById('chatForm');
const typingIndicator = document.getElementById('typingIndicator');

// Initialize WebSocket connection
let ws = null;
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;

function connectWebSocket() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log('WebSocket connected');
        reconnectAttempts = 0;
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        hideTypingIndicator();
        addMessage(data.response, 'assistant', data.data_sources);
        isProcessing = false;
        enableInput();
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        // Fallback to HTTP API
        if (isProcessing) {
            hideTypingIndicator();
            addMessage('Connection error. Switching to standard mode...', 'system');
            isProcessing = false;
            enableInput();
        }
    };
    
    ws.onclose = () => {
        console.log('WebSocket disconnected');
        // Try to reconnect
        if (reconnectAttempts < maxReconnectAttempts) {
            reconnectAttempts++;
            setTimeout(() => {
                console.log(`Reconnection attempt ${reconnectAttempts}`);
                connectWebSocket();
            }, 3000 * reconnectAttempts);
        }
    };
}

// Connect WebSocket on load
connectWebSocket();

// Utility functions
function formatTime(date) {
    return date.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit'
    });
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

function formatMessage(text) {
    // Convert markdown-style bold to HTML
    text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    
    // Convert markdown-style links
    text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" class="text-blue-600 hover:underline">$1</a>');
    
    // Convert line breaks
    text = text.replace(/\n/g, '<br>');
    
    // Convert bullet points
    text = text.replace(/^• /gm, '<span class="inline-block w-4">•</span>');
    
    return text;
}

// Message handling
function addMessage(content, role = 'user', dataSources = []) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'flex items-start message-fade-in';
    
    if (role === 'user') {
        messageDiv.innerHTML = `
            <div class="flex-shrink-0 h-8 w-8 rounded-full bg-gray-400 flex items-center justify-center ml-auto order-2">
                <svg class="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
                </svg>
            </div>
            <div class="mr-3 bg-blue-500 text-white rounded-lg p-3 max-w-md order-1">
                <p class="text-sm">${escapeHtml(content)}</p>
                <p class="text-xs opacity-75 mt-1">${formatTime(new Date())}</p>
            </div>
        `;
    } else if (role === 'assistant') {
        let dataSourcesHtml = '';
        if (dataSources && dataSources.length > 0) {
            dataSourcesHtml = `
                <div class="mt-2 pt-2 border-t border-gray-200">
                    <p class="text-xs text-gray-500">Sources: ${dataSources.join(', ')}</p>
                </div>
            `;
        }
        
        messageDiv.innerHTML = `
            <div class="flex-shrink-0 h-8 w-8 rounded-full bg-blue-500 flex items-center justify-center">
                <svg class="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                </svg>
            </div>
            <div class="ml-3 bg-gray-100 rounded-lg p-3 max-w-md">
                <div class="text-sm text-gray-800">${formatMessage(content)}</div>
                <p class="text-xs text-gray-500 mt-1">${formatTime(new Date())}</p>
                ${dataSourcesHtml}
            </div>
        `;
    } else if (role === 'system') {
        messageDiv.innerHTML = `
            <div class="mx-auto bg-yellow-50 border border-yellow-200 text-yellow-800 rounded-lg p-3 max-w-md">
                <p class="text-sm">${escapeHtml(content)}</p>
            </div>
        `;
    }
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showTypingIndicator() {
    typingIndicator.classList.remove('hidden');
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function hideTypingIndicator() {
    typingIndicator.classList.add('hidden');
}

function disableInput() {
    messageInput.disabled = true;
    sendButton.disabled = true;
    sendButton.classList.add('opacity-50', 'cursor-not-allowed');
}

function enableInput() {
    messageInput.disabled = false;
    sendButton.disabled = false;
    sendButton.classList.remove('opacity-50', 'cursor-not-allowed');
    messageInput.focus();
}

// Send message function
async function sendMessage(message) {
    if (!message.trim() || isProcessing) return;
    
    isProcessing = true;
    disableInput();
    
    // Add user message to UI
    addMessage(message, 'user');
    
    // Clear input
    messageInput.value = '';
    
    // Show typing indicator
    showTypingIndicator();
    
    // Add to context
    conversationContext.push({ role: 'user', content: message });
    
    try {
        // Try WebSocket first
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ message: message }));
        } else {
            // Fallback to HTTP API
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    context: conversationContext.slice(-5) // Last 5 messages
                }),
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            hideTypingIndicator();
            addMessage(data.response, 'assistant', data.data_sources);
            
            // Add to context
            conversationContext.push({ role: 'assistant', content: data.response });
        }
    } catch (error) {
        console.error('Error sending message:', error);
        hideTypingIndicator();
        addMessage('Sorry, I encountered an error. Please try again.', 'system');
    } finally {
        isProcessing = false;
        enableInput();
    }
}

// Quick message function
function sendQuickMessage(message) {
    messageInput.value = message;
    sendMessage(message);
}

// Event listeners
chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const message = messageInput.value.trim();
    if (message) {
        sendMessage(message);
    }
});

// Allow Enter key to send message
messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        const message = messageInput.value.trim();
        if (message) {
            sendMessage(message);
        }
    }
});

// Focus input on load
window.addEventListener('load', () => {
    messageInput.focus();
});

// Handle page visibility changes
document.addEventListener('visibilitychange', () => {
    if (!document.hidden && ws && ws.readyState !== WebSocket.OPEN) {
        // Reconnect WebSocket when page becomes visible
        connectWebSocket();
    }
});

// Service Worker Registration (for PWA support)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/js/sw.js')
            .then(registration => console.log('SW registered:', registration))
            .catch(error => console.log('SW registration failed:', error));
    });
}