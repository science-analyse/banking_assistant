// AI Banking Assistant - Complete Enhanced JavaScript

// Global variables
let currentLanguage = 'en';
let chatHistory = [];
let loadingModal;
let installPrompt = null;

// Mobile detection and capabilities
const DeviceCapabilities = {
    isMobile: /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent),
    isTouch: 'ontouchstart' in window || navigator.maxTouchPoints > 0,
    isIOS: /iPhone|iPad|iPod/i.test(navigator.userAgent),
    isAndroid: /Android/i.test(navigator.userAgent),
    supportsVibration: 'vibrate' in navigator,
    supportsServiceWorker: 'serviceWorker' in navigator,
    supportsSpeech: 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window,
    
    init() {
        this.detectDevice();
        this.setupViewportHandler();
        this.setupNetworkMonitoring();
    },
    
    detectDevice() {
        const body = document.body;
        
        if (this.isMobile || this.isTouch) {
            body.classList.add('mobile-device');
        }
        
        if (this.isIOS) {
            body.classList.add('ios-device');
        }
        
        if (this.isAndroid) {
            body.classList.add('android-device');
        }
        
        // Add touch capability class
        if (this.isTouch) {
            body.classList.add('touch-device');
        }
    },
    
    setupViewportHandler() {
        // Handle viewport height changes (virtual keyboard, etc.)
        let initialHeight = window.innerHeight;
        
        const updateViewportHeight = () => {
            const vh = window.innerHeight * 0.01;
            document.documentElement.style.setProperty('--vh', `${vh}px`);
        };
        
        updateViewportHeight();
        
        window.addEventListener('resize', debounce(() => {
            updateViewportHeight();
            
            // Detect virtual keyboard on mobile
            const currentHeight = window.innerHeight;
            const heightDifference = initialHeight - currentHeight;
            
            if (this.isMobile && heightDifference > 150) {
                document.body.classList.add('keyboard-open');
            } else {
                document.body.classList.remove('keyboard-open');
            }
        }, 100));
        
        window.addEventListener('orientationchange', () => {
            setTimeout(() => {
                updateViewportHeight();
                // Refresh maps after orientation change
                if (typeof branchMap !== 'undefined') {
                    branchMap.invalidateSize();
                }
            }, 500);
        });
    },
    
    setupNetworkMonitoring() {
        window.addEventListener('online', () => {
            this.hideOfflineIndicator();
            showAlert('success', 'Connection restored', true);
            // Retry any failed requests
            this.retryFailedRequests();
        });
        
        window.addEventListener('offline', () => {
            this.showOfflineIndicator();
            showAlert('warning', 'You are offline. Some features may not work.', false);
        });
    },
    
    showOfflineIndicator() {
        const indicator = document.getElementById('offlineIndicator');
        if (indicator) {
            indicator.classList.remove('d-none');
        }
    },
    
    hideOfflineIndicator() {
        const indicator = document.getElementById('offlineIndicator');
        if (indicator) {
            indicator.classList.add('d-none');
        }
    },
    
    retryFailedRequests() {
        // Implementation for retrying failed API requests
        console.log('Retrying failed requests...');
    },
    
    vibrate(pattern = [100]) {
        if (this.supportsVibration) {
            navigator.vibrate(pattern);
        }
    }
};

// Enhanced API Helper with retry logic and caching
const APIClient = {
    cache: new Map(),
    retryQueue: [],
    
    async call(endpoint, method = 'GET', data = null, options = {}) {
        const {
            cache = false,
            cacheDuration = 300000, // 5 minutes
            timeout = 10000,
            retries = 3,
            retryDelay = 1000
        } = options;
        
        // Check cache first
        if (cache && method === 'GET') {
            const cached = this.getFromCache(endpoint);
            if (cached) {
                return cached;
            }
        }
        
        let lastError;
        
        for (let attempt = 0; attempt < retries; attempt++) {
            try {
                showLoading();
                
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), timeout);
                
                const requestOptions = {
                    method,
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    signal: controller.signal
                };
                
                if (data && method !== 'GET') {
                    requestOptions.body = JSON.stringify(data);
                }
                
                const response = await fetch(endpoint, requestOptions);
                clearTimeout(timeoutId);
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const result = await response.json();
                hideLoading();
                
                // Cache successful GET requests
                if (cache && method === 'GET') {
                    this.setCache(endpoint, result, cacheDuration);
                }
                
                return result;
                
            } catch (error) {
                hideLoading();
                lastError = error;
                
                if (attempt < retries - 1) {
                    await this.delay(retryDelay * Math.pow(2, attempt)); // Exponential backoff
                }
            }
        }
        
        // If all retries failed
        console.error(`API call failed after ${retries} attempts:`, lastError);
        
        if (!navigator.onLine) {
            this.addToRetryQueue(endpoint, method, data, options);
            throw new Error('No internet connection. Request will be retried when online.');
        }
        
        throw lastError;
    },
    
    getFromCache(key) {
        const cached = this.cache.get(key);
        if (cached && Date.now() < cached.expiry) {
            return cached.data;
        }
        this.cache.delete(key);
        return null;
    },
    
    setCache(key, data, duration) {
        this.cache.set(key, {
            data,
            expiry: Date.now() + duration
        });
    },
    
    addToRetryQueue(endpoint, method, data, options) {
        this.retryQueue.push({ endpoint, method, data, options });
    },
    
    async retryQueuedRequests() {
        const queue = [...this.retryQueue];
        this.retryQueue = [];
        
        for (const request of queue) {
            try {
                await this.call(request.endpoint, request.method, request.data, request.options);
            } catch (error) {
                console.error('Retry failed:', error);
                // Re-add to queue if still failing
                this.addToRetryQueue(request.endpoint, request.method, request.data, request.options);
            }
        }
    },
    
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
};

// Enhanced Touch and Gesture Handler
const TouchHandler = {
    init() {
        if (!DeviceCapabilities.isTouch) return;
        
        this.setupTouchFeedback();
        this.setupSwipeGestures();
        this.setupPinchZoom();
    },
    
    setupTouchFeedback() {
        // Enhanced button press feedback
        document.addEventListener('touchstart', (e) => {
            if (e.target.closest('.btn')) {
                const btn = e.target.closest('.btn');
                btn.style.transform = 'scale(0.95)';
                DeviceCapabilities.vibrate([25]); // Subtle haptic feedback
            }
        }, { passive: true });
        
        document.addEventListener('touchend', (e) => {
            if (e.target.closest('.btn')) {
                const btn = e.target.closest('.btn');
                setTimeout(() => {
                    btn.style.transform = '';
                }, 150);
            }
        }, { passive: true });
    },
    
    setupSwipeGestures() {
        let startX, startY, startTime;
        
        document.addEventListener('touchstart', (e) => {
            if (e.touches.length === 1) {
                startX = e.touches[0].clientX;
                startY = e.touches[0].clientY;
                startTime = Date.now();
            }
        }, { passive: true });
        
        document.addEventListener('touchend', (e) => {
            if (!startX || !startY) return;
            
            const endX = e.changedTouches[0].clientX;
            const endY = e.changedTouches[0].clientY;
            const endTime = Date.now();
            
            const deltaX = endX - startX;
            const deltaY = endY - startY;
            const deltaTime = endTime - startTime;
            
            // Only process quick swipes
            if (deltaTime > 500) return;
            
            const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
            if (distance < 50) return;
            
            const angle = Math.atan2(deltaY, deltaX) * 180 / Math.PI;
            
            // Horizontal swipes
            if (Math.abs(angle) < 30 || Math.abs(angle) > 150) {
                this.handleHorizontalSwipe(deltaX > 0 ? 'right' : 'left', e.target);
            }
            // Vertical swipes
            else if (Math.abs(angle - 90) < 30 || Math.abs(angle + 90) < 30) {
                this.handleVerticalSwipe(deltaY > 0 ? 'down' : 'up', e.target);
            }
            
            startX = startY = null;
        }, { passive: true });
    },
    
    handleHorizontalSwipe(direction, target) {
        // Handle navigation swipes
        if (target.closest('.currency-card')) {
            this.handleCurrencySwipe(direction);
        } else if (target.closest('.chat-message')) {
            // Future: implement chat message actions
        }
    },
    
    handleVerticalSwipe(direction, target) {
        // Handle pull-to-refresh or dismiss actions
        if (direction === 'down' && window.scrollY === 0) {
            this.handlePullToRefresh();
        }
    },
    
    handleCurrencySwipe(direction) {
        console.log(`Currency swipe: ${direction}`);
        // Implement currency carousel navigation
        DeviceCapabilities.vibrate([50]);
    },
    
    handlePullToRefresh() {
        // Simple pull-to-refresh implementation
        showAlert('info', 'Refreshing data...', true);
        setTimeout(() => {
            window.location.reload();
        }, 1000);
    },
    
    setupPinchZoom() {
        // Disable pinch zoom on input elements to prevent iOS zoom
        const inputs = document.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('touchstart', (e) => {
                if (e.touches.length > 1) {
                    e.preventDefault();
                }
            });
        });
    }
};

// Progressive Web App Handler
const PWAHandler = {
    init() {
        this.registerServiceWorker();
        this.setupInstallPrompt();
        this.setupPWAFeatures();
    },
    
    async registerServiceWorker() {
        if (!DeviceCapabilities.supportsServiceWorker) return;
        
        try {
            const registration = await navigator.serviceWorker.register('/sw.js');
            console.log('Service Worker registered:', registration);
            
            registration.addEventListener('updatefound', () => {
                const newWorker = registration.installing;
                newWorker.addEventListener('statechange', () => {
                    if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                        this.showUpdateAvailable();
                    }
                });
            });
        } catch (error) {
            console.error('Service Worker registration failed:', error);
        }
    },
    
    setupInstallPrompt() {
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            installPrompt = e;
            this.showInstallButton();
        });
        
        window.addEventListener('appinstalled', () => {
            console.log('App installed successfully');
            installPrompt = null;
            this.hideInstallButton();
            showAlert('success', 'App installed successfully!', true);
        });
    },
    
    showInstallButton() {
        const installContainer = document.getElementById('installPrompt');
        if (!installContainer) return;
        
        const installBtn = document.createElement('button');
        installBtn.className = 'btn btn-outline-primary btn-sm position-fixed';
        installBtn.style.cssText = 'bottom: 80px; right: 1rem; z-index: 1060; box-shadow: 0 4px 12px rgba(0,0,0,0.3);';
        installBtn.innerHTML = '<i class="bi bi-download me-1"></i>Install App';
        installBtn.setAttribute('aria-label', 'Install Banking Assistant App');
        
        installBtn.addEventListener('click', () => this.installApp());
        
        installContainer.appendChild(installBtn);
    },
    
    hideInstallButton() {
        const installContainer = document.getElementById('installPrompt');
        if (installContainer) {
            installContainer.innerHTML = '';
        }
    },
    
    async installApp() {
        if (!installPrompt) return;
        
        try {
            const result = await installPrompt.prompt();
            const outcome = await result.userChoice;
            
            if (outcome === 'accepted') {
                console.log('User accepted the install prompt');
                DeviceCapabilities.vibrate([100, 50, 100]);
            } else {
                console.log('User dismissed the install prompt');
            }
            
            installPrompt = null;
            this.hideInstallButton();
        } catch (error) {
            console.error('Install prompt failed:', error);
        }
    },
    
    showUpdateAvailable() {
        const updateBanner = document.createElement('div');
        updateBanner.className = 'alert alert-info alert-dismissible position-fixed top-0 start-0 end-0';
        updateBanner.style.zIndex = '1070';
        updateBanner.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <span><i class="bi bi-arrow-clockwise me-2"></i>New version available!</span>
                <div>
                    <button class="btn btn-sm btn-info me-2" onclick="window.location.reload()">Update</button>
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            </div>
        `;
        
        document.body.appendChild(updateBanner);
        
        setTimeout(() => {
            updateBanner.remove();
        }, 10000);
    },
    
    setupPWAFeatures() {
        // Add PWA-specific features
        if (window.matchMedia('(display-mode: standalone)').matches) {
            document.body.classList.add('pwa-mode');
            
            // Handle back button in PWA mode
            window.addEventListener('popstate', (e) => {
                if (window.history.length === 1) {
                    // If this is the last page, show exit confirmation
                    if (confirm('Exit Banking Assistant?')) {
                        window.close();
                    }
                }
            });
        }
    }
};

// Enhanced Chat System with Mobile Optimizations
const ChatSystem = {
    recognition: null,
    isListening: false,
    
    init() {
        this.setupChatInterface();
        this.setupVoiceInput();
        this.setupMobileOptimizations();
        this.loadChatHistory();
    },
    
    setupChatInterface() {
        const chatForm = document.getElementById('chatForm');
        const messageInput = document.getElementById('messageInput');
        
        if (!chatForm || !messageInput) return;
        
        // Auto-resize textarea
        messageInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        });
        
        // Enhanced submit handling
        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.sendMessage();
        });
        
        // Mobile-friendly keyboard handling
        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey && !DeviceCapabilities.isMobile) {
                e.preventDefault();
                chatForm.dispatchEvent(new Event('submit'));
            }
        });
        
        // Clear chat functionality
        const clearBtn = document.getElementById('clearChat');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearChat());
        }
    },
    
    setupVoiceInput() {
        if (!DeviceCapabilities.supportsSpeech) return;
        
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        
        this.recognition.continuous = false;
        this.recognition.interimResults = false;
        this.recognition.lang = currentLanguage === 'az' ? 'az-AZ' : 'en-US';
        
        this.addVoiceButton();
        this.setupSpeechEvents();
    },
    
    addVoiceButton() {
        const chatForm = document.getElementById('chatForm');
        if (!chatForm) return;
        
        const voiceBtn = document.createElement('button');
        voiceBtn.type = 'button';
        voiceBtn.className = 'btn btn-outline-secondary';
        voiceBtn.innerHTML = '<i class="bi bi-mic"></i>';
        voiceBtn.setAttribute('aria-label', 'Voice input');
        voiceBtn.title = 'Voice input';
        
        voiceBtn.addEventListener('click', () => this.toggleVoiceInput());
        
        // Insert before submit button
        const submitBtn = chatForm.querySelector('button[type="submit"]');
        chatForm.insertBefore(voiceBtn, submitBtn);
        
        this.voiceBtn = voiceBtn;
    },
    
    setupSpeechEvents() {
        if (!this.recognition) return;
        
        this.recognition.addEventListener('start', () => {
            this.isListening = true;
            this.voiceBtn.innerHTML = '<i class="bi bi-mic-fill text-danger"></i>';
            this.voiceBtn.disabled = true;
            DeviceCapabilities.vibrate([50]);
            showAlert('info', 'Listening... Speak now', true);
        });
        
        this.recognition.addEventListener('result', (e) => {
            const transcript = e.results[0][0].transcript;
            document.getElementById('messageInput').value = transcript;
            DeviceCapabilities.vibrate([100]); // Success haptic
            showAlert('success', 'Voice input captured', true);
        });
        
        this.recognition.addEventListener('end', () => {
            this.isListening = false;
            this.voiceBtn.innerHTML = '<i class="bi bi-mic"></i>';
            this.voiceBtn.disabled = false;
        });
        
        this.recognition.addEventListener('error', (e) => {
            this.isListening = false;
            this.voiceBtn.innerHTML = '<i class="bi bi-mic"></i>';
            this.voiceBtn.disabled = false;
            
            let errorMessage = 'Voice input failed. Please try again.';
            switch (e.error) {
                case 'no-speech':
                    errorMessage = 'No speech detected. Please try again.';
                    break;
                case 'network':
                    errorMessage = 'Network error. Check your connection.';
                    break;
                case 'not-allowed':
                    errorMessage = 'Microphone access denied. Please allow microphone access.';
                    break;
            }
            
            showAlert('error', errorMessage, true);
        });
    },
    
    toggleVoiceInput() {
        if (this.isListening) {
            this.recognition.stop();
        } else {
            this.recognition.lang = currentLanguage === 'az' ? 'az-AZ' : 'en-US';
            this.recognition.start();
        }
    },
    
    setupMobileOptimizations() {
        if (!DeviceCapabilities.isMobile) return;
        
        // Improve chat scrolling on mobile
        const chatContainer = document.getElementById('chatMessages');
        if (chatContainer) {
            chatContainer.style.overflowScrolling = 'touch';
            chatContainer.style.webkitOverflowScrolling = 'touch';
        }
        
        // Handle virtual keyboard
        const messageInput = document.getElementById('messageInput');
        if (messageInput) {
            messageInput.addEventListener('focus', () => {
                setTimeout(() => {
                    messageInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }, 300);
            });
        }
    },
    
    async sendMessage() {
        const messageInput = document.getElementById('messageInput');
        const message = messageInput.value.trim();
        
        if (!message) return;
        
        // Add user message
        this.addMessageToChat('user', message);
        messageInput.value = '';
        messageInput.style.height = 'auto';
        
        // Show typing indicator
        this.showTypingIndicator();
        
        try {
            const response = await APIClient.call('/api/chat', 'POST', {
                message: message,
                language: currentLanguage,
                session_id: this.generateSessionId(),
                user_location: await this.getUserLocation()
            });
            
            this.hideTypingIndicator();
            this.addMessageToChat('assistant', response.response);
            
            if (response.suggestions) {
                this.showSuggestions(response.suggestions);
            }
            
            // Haptic feedback for successful response
            DeviceCapabilities.vibrate([50, 25, 50]);
            
        } catch (error) {
            this.hideTypingIndicator();
            this.addMessageToChat('assistant', this.getErrorMessage(error));
            console.error('Chat error:', error);
        }
    },
    
    addMessageToChat(sender, message) {
        const chatContainer = document.getElementById('chatMessages');
        if (!chatContainer) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${sender} fade-in`;
        
        const time = new Date().toLocaleTimeString();
        
        // Enhanced message processing
        let processedMessage = this.processMessage(message);
        
        messageDiv.innerHTML = `
            <div class="d-flex justify-content-between align-items-start mb-1">
                <strong>${sender === 'user' ? 'You' : 'AI Assistant'}</strong>
                <small class="opacity-75">${time}</small>
            </div>
            <div>${processedMessage}</div>
        `;
        
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        
        // Save to history
        chatHistory.push({ sender, message, time });
        this.saveChatHistory();
    },
    
    processMessage(message) {
        // Convert URLs to links
        message = message.replace(
            /https?:\/\/[^\s]+/g, 
            '<a href="$&" target="_blank" rel="noopener noreferrer" class="text-decoration-none">$&</a>'
        );
        
        // Convert phone numbers to clickable links
        message = message.replace(
            /\+994\s?\d{2}\s?\d{3}\s?\d{2}\s?\d{2}/g,
            '<a href="tel:$&" class="text-decoration-none">$&</a>'
        );
        
        // Highlight currencies and rates
        message = message.replace(
            /(\d+\.?\d*%|\d+\.?\d*\s?(AZN|USD|EUR|RUB|TRY|GBP))/g,
            '<strong class="text-primary">$1</strong>'
        );
        
        // Convert line breaks to <br>
        message = message.replace(/\n/g, '<br>');
        
        return message;
    },
    
    showTypingIndicator() {
        const chatContainer = document.getElementById('chatMessages');
        if (!chatContainer) return;
        
        const typingDiv = document.createElement('div');
        typingDiv.id = 'typingIndicator';
        typingDiv.className = 'typing-indicator';
        typingDiv.innerHTML = `
            <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
            <span class="ms-2">AI is typing...</span>
        `;
        
        chatContainer.appendChild(typingDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    },
    
    hideTypingIndicator() {
        const typingIndicator = document.getElementById('typingIndicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    },
    
    showSuggestions(suggestions) {
        const container = document.getElementById('suggestions');
        if (!container || !suggestions.length) return;
        
        container.innerHTML = '';
        const wrapper = document.createElement('div');
        wrapper.className = 'd-flex flex-wrap gap-2 mb-3';
        
        const label = document.createElement('small');
        label.className = 'text-muted w-100 mb-2';
        label.innerHTML = '💡 Suggested questions:';
        wrapper.appendChild(label);
        
        suggestions.forEach((suggestion, index) => {
            const chip = document.createElement('button');
            chip.className = 'btn btn-outline-primary btn-sm fade-in';
            chip.style.animationDelay = `${index * 0.1}s`;
            chip.style.borderRadius = '20px';
            chip.textContent = suggestion;
            chip.addEventListener('click', () => this.sendSuggestion(suggestion));
            wrapper.appendChild(chip);
        });
        
        container.appendChild(wrapper);
        
        // Auto-hide after 30 seconds
        setTimeout(() => {
            if (container.contains(wrapper)) {
                wrapper.remove();
            }
        }, 30000);
    },
    
    sendSuggestion(suggestion) {
        const messageInput = document.getElementById('messageInput');
        if (messageInput) {
            messageInput.value = suggestion;
            document.getElementById('chatForm').dispatchEvent(new Event('submit'));
        }
    },
    
    clearChat() {
        const chatContainer = document.getElementById('chatMessages');
        const suggestionsContainer = document.getElementById('suggestions');
        
        if (chatContainer) chatContainer.innerHTML = '';
        if (suggestionsContainer) suggestionsContainer.innerHTML = '';
        
        chatHistory = [];
        localStorage.removeItem('chatHistory');
        
        showAlert('info', 'Chat cleared', true);
    },
    
    loadChatHistory() {
        const saved = localStorage.getItem('chatHistory');
        if (!saved) return;
        
        try {
            chatHistory = JSON.parse(saved);
            const chatContainer = document.getElementById('chatMessages');
            if (!chatContainer) return;
            
            chatHistory.forEach(msg => {
                const messageDiv = document.createElement('div');
                messageDiv.className = `chat-message ${msg.sender}`;
                messageDiv.innerHTML = `
                    <div class="d-flex justify-content-between align-items-start mb-1">
                        <strong>${msg.sender === 'user' ? 'You' : 'AI Assistant'}</strong>
                        <small class="opacity-75">${msg.time}</small>
                    </div>
                    <div>${this.processMessage(msg.message)}</div>
                `;
                chatContainer.appendChild(messageDiv);
            });
            
            if (chatHistory.length > 0) {
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
        } catch (error) {
            console.error('Error loading chat history:', error);
            localStorage.removeItem('chatHistory');
        }
    },
    
    saveChatHistory() {
        try {
            // Keep only last 50 messages to prevent storage bloat
            const recentHistory = chatHistory.slice(-50);
            localStorage.setItem('chatHistory', JSON.stringify(recentHistory));
        } catch (error) {
            console.error('Error saving chat history:', error);
        }
    },
    
    generateSessionId() {
        let sessionId = localStorage.getItem('chatSessionId');
        if (!sessionId) {
            sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('chatSessionId', sessionId);
        }
        return sessionId;
    },
    
    async getUserLocation() {
        return new Promise((resolve) => {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        resolve({
                            latitude: position.coords.latitude,
                            longitude: position.coords.longitude
                        });
                    },
                    () => resolve(null),
                    { timeout: 5000, enableHighAccuracy: false }
                );
            } else {
                resolve(null);
            }
        });
    },
    
    getErrorMessage(error) {
        if (currentLanguage === 'az') {
            return 'Təəssüf ki, xəta baş verdi. Zəhmət olmasa yenidən cəhd edin.';
        }
        return 'Sorry, I encountered an error. Please try again.';
    }
};

// Application Initialization
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Initialize core systems
    DeviceCapabilities.init();
    TouchHandler.init();
    PWAHandler.init();
    
    // Initialize Bootstrap components
    try {
        loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'), {
            backdrop: 'static',
            keyboard: false
        });
    } catch (error) {
        console.error('Error initializing loading modal:', error);
    }
    
    // Set language from localStorage
    const savedLanguage = localStorage.getItem('language') || 'en';
    setLanguage(savedLanguage);
    
    // Initialize page-specific features
    const currentPage = window.location.pathname;
    
    switch (currentPage) {
        case '/loans':
            initializeLoanComparison();
            break;
        case '/branches':
            initializeBranchFinder();
            break;
        case '/chat':
            ChatSystem.init();
            break;
        case '/currency':
            initializeCurrencyConverter();
            break;
    }
    
    // Initialize common features
    initializeAlerts();
    initializeFormValidation();
    optimizeForMobile();
}

// Enhanced Form Validation
function initializeFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                
                // Find first invalid field and focus it
                const firstInvalid = form.querySelector(':invalid');
                if (firstInvalid) {
                    firstInvalid.focus();
                    firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
                
                showAlert('danger', 'Please fill in all required fields correctly.', true);
                DeviceCapabilities.vibrate([100, 50, 100]); // Error haptic
            }
            form.classList.add('was-validated');
        });
        
        // Real-time validation
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                if (this.checkValidity()) {
                    this.classList.remove('is-invalid');
                    this.classList.add('is-valid');
                } else {
                    this.classList.remove('is-valid');
                    this.classList.add('is-invalid');
                }
            });
        });
    });
}

// Mobile Optimizations
function optimizeForMobile() {
    if (!DeviceCapabilities.isMobile) return;
    
    // Optimize form inputs
    const numberInputs = document.querySelectorAll('input[type="number"]');
    numberInputs.forEach(input => {
        input.setAttribute('inputmode', 'numeric');
        input.setAttribute('pattern', '[0-9]*');
    });
    
    const telInputs = document.querySelectorAll('input[type="tel"], a[href^="tel:"]');
    telInputs.forEach(input => {
        input.setAttribute('inputmode', 'tel');
    });
    
    // Prevent zoom on input focus (iOS)
    const allInputs = document.querySelectorAll('input, select, textarea');
    allInputs.forEach(input => {
        if (input.style.fontSize !== '16px') {
            input.style.fontSize = '16px';
        }
    });
    
    // Optimize images
    const images = document.querySelectorAll('img');
    images.forEach(img => {
        if (!img.hasAttribute('loading')) {
            img.setAttribute('loading', 'lazy');
        }
        
        img.addEventListener('error', function() {
            this.style.display = 'none';
        });
    });
}

// Enhanced Alert System
function initializeAlerts() {
    // Auto-hide alerts
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('alert-dismissible')) {
            setTimeout(() => {
                e.target.remove();
            }, 5000);
        }
    });
}

function showAlert(type, message, autoHide = true) {
    const alertContainer = document.getElementById('alertContainer');
    if (!alertContainer) return;
    
    const alertId = 'alert-' + Date.now();
    const iconMap = {
        success: 'check-circle',
        error: 'exclamation-triangle',
        warning: 'exclamation-triangle',
        info: 'info-circle',
        danger: 'exclamation-triangle'
    };
    
    const alertHtml = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            <i class="bi bi-${iconMap[type]} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    
    alertContainer.insertAdjacentHTML('beforeend', alertHtml);
    
    if (autoHide) {
        setTimeout(() => {
            const alert = document.getElementById(alertId);
            if (alert) {
                alert.remove();
            }
        }, 5000);
    }
    
    // Haptic feedback for alerts
    if (type === 'error' || type === 'danger') {
        DeviceCapabilities.vibrate([100, 50, 100, 50, 100]);
    } else if (type === 'success') {
        DeviceCapabilities.vibrate([100, 50, 100]);
    }
}

function showLoading(text = null) {
    if (!loadingModal) return;
    
    if (text) {
        const loadingText = document.getElementById('loadingText');
        if (loadingText) {
            loadingText.textContent = text;
        }
    }
    loadingModal.show();
}

function hideLoading() {
    if (loadingModal) {
        loadingModal.hide();
    }
}

// Language Management
function setLanguage(lang) {
    currentLanguage = lang;
    localStorage.setItem('language', lang);
    
    // Update UI
    const currentLangElement = document.getElementById('currentLanguage');
    if (currentLangElement) {
        currentLangElement.textContent = lang.toUpperCase();
    }
    
    // Update document language
    document.documentElement.lang = lang === 'az' ? 'az' : 'en';
    
    // Update speech recognition language
    if (ChatSystem.recognition) {
        ChatSystem.recognition.lang = lang === 'az' ? 'az-AZ' : 'en-US';
    }
    
    // Update loading text
    updateLanguageText();
    
    // Trigger language change event
    document.dispatchEvent(new CustomEvent('languageChanged', { 
        detail: { language: lang } 
    }));
}

function updateLanguageText() {
    const translations = {
        en: {
            loading: 'Processing your request...',
            error: 'An error occurred. Please try again.',
            success: 'Operation completed successfully!',
            noResults: 'No results found.',
            tryAgain: 'Please try again.'
        },
        az: {
            loading: 'Sorğunuz işlənir...',
            error: 'Xəta baş verdi. Zəhmət olmasa yenidən cəhd edin.',
            success: 'Əməliyyat uğurla tamamlandı!',
            noResults: 'Heç bir nəticə tapılmadı.',
            tryAgain: 'Zəhmət olmasa yenidən cəhd edin.'
        }
    };
    
    const loadingText = document.getElementById('loadingText');
    if (loadingText) {
        loadingText.textContent = translations[currentLanguage].loading;
    }
}

// Loan Comparison System
function initializeLoanComparison() {
    const loanForm = document.getElementById('loanComparisonForm');
    if (!loanForm) return;
    
    loanForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(loanForm);
        const loanData = {
            amount: parseFloat(formData.get('amount')),
            loan_type: formData.get('loan_type'),
            currency: formData.get('currency'),
            term_months: parseInt(formData.get('term_months')) || 60
        };
        
        try {
            const result = await APIClient.call('/api/loans/compare', 'POST', loanData);
            displayLoanResults(result);
            DeviceCapabilities.vibrate([100]); // Success haptic
        } catch (error) {
            console.error('Loan comparison error:', error);
            showAlert('error', 'Failed to compare loans. Please try again.', true);
        }
    });
    
    // Real-time preview updates
    ['amount', 'term_months'].forEach(field => {
        const element = document.getElementById(field);
        if (element) {
            element.addEventListener('input', debounce(updateLoanPreview, 500));
        }
    });
}

function displayLoanResults(results) {
    const container = document.getElementById('loanResults');
    if (!container) return;
    
    let html = `
        <div class="row mb-4">
            <div class="col-12">
                <h3><i class="bi bi-calculator me-2"></i>Loan Comparison Results</h3>
                <p class="text-muted">Found ${results.total_banks} options for ${results.loan_amount.toLocaleString()} ${results.currency} ${results.loan_type} loan</p>
            </div>
        </div>
    `;
    
    if (results.best_rate) {
        html += `
            <div class="row mb-4">
                <div class="col-12">
                    <div class="loan-result-card best-rate bounce-in">
                        <h4 class="text-success mb-3">
                            <i class="bi bi-trophy me-2"></i>
                            Best Rate: ${results.best_rate.bank_name}
                        </h4>
                        <div class="row">
                            <div class="col-md-3 col-6 mb-3">
                                <h5 class="text-primary">${results.best_rate.avg_interest_rate}%</h5>
                                <small class="text-muted">Interest Rate</small>
                            </div>
                            <div class="col-md-3 col-6 mb-3">
                                <h5>${results.best_rate.monthly_payment} ${results.currency}</h5>
                                <small class="text-muted">Monthly Payment</small>
                            </div>
                            <div class="col-md-3 col-6 mb-3">
                                <h5>${results.best_rate.total_payment} ${results.currency}</h5>
                                <small class="text-muted">Total Payment</small>
                            </div>
                            <div class="col-md-3 col-6 mb-3">
                                <a href="tel:${results.best_rate.phone}" class="btn btn-success w-100">
                                    <i class="bi bi-telephone me-1"></i>
                                    Call Now
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Chart section
    html += `
        <div class="row mb-4">
            <div class="col-12">
                <div class="chart-container">
                    <canvas id="loanChart" width="400" height="200"></canvas>
                </div>
            </div>
        </div>
    `;
    
    html += '<div class="row">';
    results.comparisons.forEach((loan, index) => {
        html += `
            <div class="col-lg-6 mb-3">
                <div class="loan-result-card slide-up" style="animation-delay: ${index * 0.1}s">
                    <div class="d-flex justify-content-between align-items-start mb-3">
                        <h5>${loan.bank_name}</h5>
                        <span class="badge bg-primary">${loan.avg_interest_rate}%</span>
                    </div>
                    <div class="row text-center">
                        <div class="col-6">
                            <div class="border-end">
                                <h6>${loan.monthly_payment} ${results.currency}</h6>
                                <small class="text-muted">Monthly</small>
                            </div>
                        </div>
                        <div class="col-6">
                            <h6>${loan.total_payment} ${results.currency}</h6>
                            <small class="text-muted">Total</small>
                        </div>
                    </div>
                    <div class="mt-3 d-grid gap-2 d-md-flex">
                        <a href="tel:${loan.phone}" class="btn btn-outline-primary btn-sm flex-fill">
                            <i class="bi bi-telephone me-1"></i>Call
                        </a>
                        ${loan.website ? `
                            <a href="${loan.website}" target="_blank" class="btn btn-outline-secondary btn-sm flex-fill">
                                <i class="bi bi-globe me-1"></i>Website
                            </a>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
    });
    html += '</div>';
    
    container.innerHTML = html;
    
    // Create chart
    setTimeout(() => createLoanChart(results), 100);
}

function createLoanChart(results) {
    const ctx = document.getElementById('loanChart');
    if (!ctx) return;
    
    const chartData = {
        labels: results.comparisons.map(c => c.bank_name),
        datasets: [{
            label: 'Interest Rate (%)',
            data: results.comparisons.map(c => c.avg_interest_rate),
            backgroundColor: results.comparisons.map((_, index) => 
                index === 0 ? '#27ae60' : '#3498db'
            ),
            borderColor: '#2c3e50',
            borderWidth: 1
        }]
    };
    
    new Chart(ctx, {
        type: 'bar',
        data: chartData,
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Interest Rates Comparison'
                },
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Interest Rate (%)'
                    }
                }
            }
        }
    });
}

function updateLoanPreview() {
    const amount = parseFloat(document.getElementById('amount')?.value) || 0;
    const months = parseInt(document.getElementById('term_months')?.value) || 60;
    
    if (amount > 0) {
        // Simple calculation with estimated 10% rate for preview
        const monthlyRate = 0.10 / 12;
        const monthlyPayment = amount * (monthlyRate * Math.pow(1 + monthlyRate, months)) / (Math.pow(1 + monthlyRate, months) - 1);
        
        // Show preview if there's a preview element
        const previewElement = document.getElementById('loanPreview');
        if (previewElement) {
            previewElement.innerHTML = `
                <small class="text-muted">
                    Estimated monthly payment: <strong>${monthlyPayment.toFixed(2)} AZN</strong>
                </small>
            `;
        }
    }
}

// Branch Finder System
function initializeBranchFinder() {
    const branchForm = document.getElementById('branchFinderForm');
    if (!branchForm) return;
    
    // Initialize map
    setTimeout(() => {
        if (typeof L !== 'undefined') {
            window.branchMap = L.map('branchMap').setView([40.4093, 49.8671], 12);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }).addTo(window.branchMap);
            
            // Mobile optimizations for map
            if (DeviceCapabilities.isMobile) {
                window.branchMap.scrollWheelZoom.disable();
                window.branchMap.tap.enable();
            }
        }
    }, 1000);
    
    branchForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(branchForm);
        const searchData = {
            bank_name: formData.get('bank_name') || 'all',
            latitude: parseFloat(formData.get('latitude')) || 40.4093,
            longitude: parseFloat(formData.get('longitude')) || 49.8671,
            limit: 10
        };
        
        try {
            const result = await APIClient.call('/api/branches/find', 'POST', searchData);
            displayBranchResults(result);
            DeviceCapabilities.vibrate([100]); // Success haptic
        } catch (error) {
            console.error('Branch finder error:', error);
            showAlert('error', 'Failed to find branches. Please try again.', true);
        }
    });
    
    // Location button
    const locationBtn = document.getElementById('useMyLocation');
    if (locationBtn) {
        locationBtn.addEventListener('click', requestUserLocation);
    }
}

function displayBranchResults(results) {
    const container = document.getElementById('branchResults');
    if (!container || !window.branchMap) return;
    
    // Clear existing markers
    window.branchMap.eachLayer(layer => {
        if (layer instanceof L.Marker) {
            window.branchMap.removeLayer(layer);
        }
    });
    
    let html = `
        <div class="row mb-4">
            <div class="col-12">
                <h3><i class="bi bi-geo-alt me-2"></i>Found ${results.showing} branches nearby</h3>
                <p class="text-muted">Showing closest branches within range</p>
            </div>
        </div>
        <div class="row">
    `;
    
    results.branches.forEach((branch, index) => {
        // Add marker to map
        const marker = L.marker([branch.coordinates.lat, branch.coordinates.lng])
            .addTo(window.branchMap)
            .bindPopup(`
                <div style="min-width: 200px;">
                    <strong>${branch.bank_name}</strong><br>
                    <strong>${branch.branch_name}</strong><br>
                    <small class="text-muted">${branch.address}</small><br>
                    <strong>${branch.distance_km} km away</strong><br>
                    <div class="mt-2">
                        <a href="tel:${branch.phone}" class="btn btn-primary btn-sm">
                            <i class="bi bi-telephone"></i> Call
                        </a>
                        <a href="https://maps.google.com/maps?q=${branch.coordinates.lat},${branch.coordinates.lng}" 
                           target="_blank" class="btn btn-outline-secondary btn-sm">
                            <i class="bi bi-map"></i> Directions
                        </a>
                    </div>
                </div>
            `);
        
        html += `
            <div class="col-12 mb-3">
                <div class="branch-card slide-up" style="animation-delay: ${index * 0.1}s">
                    <div class="row align-items-center">
                        <div class="col-12 col-md-8 mb-3 mb-md-0">
                            <div class="d-flex justify-content-between align-items-start mb-2">
                                <div>
                                    <h5 class="mb-1 text-primary">${branch.bank_name}</h5>
                                    <h6 class="text-dark mb-2">${branch.branch_name}</h6>
                                </div>
                                <span class="badge bg-success">${branch.distance_km} km</span>
                            </div>
                            <p class="text-muted mb-2">
                                <i class="bi bi-geo-alt me-1"></i>
                                ${branch.address}
                            </p>
                            <div class="row text-sm">
                                <div class="col-12 col-sm-6 mb-1">
                                    <small class="text-muted">
                                        <i class="bi bi-clock me-1"></i>
                                        ${branch.hours}
                                    </small>
                                </div>
                                <div class="col-12 col-sm-6">
                                    <small class="text-muted">
                                        <i class="bi bi-telephone me-1"></i>
                                        <a href="tel:${branch.phone}" class="text-decoration-none">${branch.phone}</a>
                                    </small>
                                </div>
                            </div>
                        </div>
                        <div class="col-12 col-md-4">
                            <div class="d-grid gap-2">
                                <button class="btn btn-primary btn-sm" onclick="focusOnBranch(${branch.coordinates.lat}, ${branch.coordinates.lng})">
                                    <i class="bi bi-geo-alt me-1"></i>
                                    <span class="d-none d-sm-inline">View on Map</span>
                                    <span class="d-sm-none">Map</span>
                                </button>
                                <div class="btn-group w-100" role="group">
                                    <a href="tel:${branch.phone}" class="btn btn-outline-primary btn-sm">
                                        <i class="bi bi-telephone"></i>
                                        <span class="d-none d-sm-inline ms-1">Call</span>
                                    </a>
                                    <a href="https://maps.google.com/maps?q=${branch.coordinates.lat},${branch.coordinates.lng}" 
                                       target="_blank" class="btn btn-outline-secondary btn-sm">
                                        <i class="bi bi-map"></i>
                                        <span class="d-none d-sm-inline ms-1">Directions</span>
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
    
    // Fit map to show all branches
    if (results.branches.length > 0) {
        const group = new L.featureGroup();
        window.branchMap.eachLayer(layer => {
            if (layer instanceof L.Marker) {
                group.addLayer(layer);
            }
        });
        window.branchMap.fitBounds(group.getBounds().pad(0.1));
    }
}

function focusOnBranch(lat, lng) {
    if (window.branchMap) {
        window.branchMap.setView([lat, lng], 16);
        
        // Find and open the popup for this marker
        window.branchMap.eachLayer(layer => {
            if (layer instanceof L.Marker && 
                Math.abs(layer.getLatLng().lat - lat) < 0.001 && 
                Math.abs(layer.getLatLng().lng - lng) < 0.001) {
                layer.openPopup();
            }
        });
        
        DeviceCapabilities.vibrate([50]); // Location haptic
    }
}

function requestUserLocation() {
    if (!navigator.geolocation) {
        showAlert('error', 'Geolocation is not supported by this browser.', true);
        return;
    }
    
    showAlert('info', 'Getting your location...', true);
    
    navigator.geolocation.getCurrentPosition(
        (position) => {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            
            document.getElementById('latitude').value = lat.toFixed(6);
            document.getElementById('longitude').value = lng.toFixed(6);
            
            if (window.branchMap) {
                window.branchMap.setView([lat, lng], 13);
            }
            
            showAlert('success', 'Location updated successfully!', true);
            DeviceCapabilities.vibrate([100, 50, 100]); // Success haptic
        },
        (error) => {
            let message = 'Unable to get your location. Using default location (Baku).';
            switch (error.code) {
                case error.PERMISSION_DENIED:
                    message = 'Location access denied. Please allow location access.';
                    break;
                case error.POSITION_UNAVAILABLE:
                    message = 'Location information unavailable.';
                    break;
                case error.TIMEOUT:
                    message = 'Location request timed out.';
                    break;
            }
            showAlert('warning', message, true);
        },
        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 300000
        }
    );
}

// Currency Converter System
function initializeCurrencyConverter() {
    const converterForm = document.getElementById('currencyConverter');
    if (!converterForm) return;
    
    converterForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(converterForm);
        const amount = parseFloat(formData.get('amount'));
        const fromCurrency = formData.get('fromCurrency');
        const toCurrency = formData.get('toCurrency');
        
        try {
            const rates = await APIClient.call('/api/currency/rates', 'GET', null, { cache: true });
            const result = convertCurrency(amount, fromCurrency, toCurrency, rates.rates);
            displayConversionResult(amount, fromCurrency, result, toCurrency, rates.rates);
            DeviceCapabilities.vibrate([100]); // Success haptic
        } catch (error) {
            console.error('Currency conversion error:', error);
            showAlert('error', 'Failed to convert currency. Please try again.', true);
        }
    });
    
    // Auto-convert on input change
    ['amount', 'fromCurrency', 'toCurrency'].forEach(field => {
        const element = document.getElementById(field);
        if (element) {
            element.addEventListener('change', debounce(autoConvert, 300));
        }
    });
    
    const amountInput = document.getElementById('amount');
    if (amountInput) {
        amountInput.addEventListener('input', debounce(autoConvert, 500));
    }
}

function convertCurrency(amount, from, to, rates) {
    if (from === 'AZN') {
        return to === 'AZN' ? amount : amount / rates[to];
    } else if (to === 'AZN') {
        return amount * rates[from];
    } else {
        // Convert via AZN
        const aznAmount = amount * rates[from];
        return aznAmount / rates[to];
    }
}

async function autoConvert() {
    const amount = parseFloat(document.getElementById('amount')?.value) || 0;
    const fromCurrency = document.getElementById('fromCurrency')?.value;
    const toCurrency = document.getElementById('toCurrency')?.value;
    
    if (amount > 0 && fromCurrency && toCurrency) {
        try {
            const rates = await APIClient.call('/api/currency/rates', 'GET', null, { cache: true });
            const result = convertCurrency(amount, fromCurrency, toCurrency, rates.rates);
            
            const resultInput = document.getElementById('convertedAmount');
            if (resultInput) {
                resultInput.value = result.toFixed(4);
            }
            
            showConversionDetails(amount, fromCurrency, result, toCurrency, rates.rates);
        } catch (error) {
            console.error('Auto conversion error:', error);
        }
    }
}

function displayConversionResult(amount, fromCurrency, result, toCurrency, rates) {
    const container = document.getElementById('conversionResult');
    if (!container) return;
    
    const rate = fromCurrency === 'AZN' ? (1 / rates[toCurrency]) : 
                 toCurrency === 'AZN' ? rates[fromCurrency] :
                 (rates[fromCurrency] / rates[toCurrency]);
    
    container.innerHTML = `
        <div class="converter-result">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <div>
                    <h4>${amount} ${fromCurrency} = ${result.toFixed(4)} ${toCurrency}</h4>
                </div>
                <small class="text-muted">Rate: ${rate.toFixed(6)}</small>
            </div>
            <small>
                <i class="bi bi-clock me-1"></i>
                Updated: ${new Date().toLocaleString()}
            </small>
        </div>
    `;
}

function showConversionDetails(amount, fromCurrency, result, toCurrency, rates) {
    const container = document.getElementById('conversionResult');
    if (!container) return;
    
    const rate = fromCurrency === 'AZN' ? (1 / rates[toCurrency]) : 
                 toCurrency === 'AZN' ? rates[fromCurrency] :
                 (rates[fromCurrency] / rates[toCurrency]);
    
    container.innerHTML = `
        <div class="alert alert-info">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <strong>${amount} ${fromCurrency} = ${result.toFixed(4)} ${toCurrency}</strong>
                </div>
                <small class="text-muted">Rate: ${rate.toFixed(6)}</small>
            </div>
            <small class="text-muted">
                <i class="bi bi-clock me-1"></i>
                Updated: ${new Date().toLocaleString()}
            </small>
        </div>
    `;
}

// Utility Functions
function debounce(func, wait) {
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

function formatCurrency(amount, currency = 'AZN') {
    try {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency,
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(amount);
    } catch (error) {
        return `${amount.toFixed(2)} ${currency}`;
    }
}

function formatDate(dateString) {
    try {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (error) {
        return dateString;
    }
}

// Export functions for global access
window.APIClient = APIClient;
window.showAlert = showAlert;
window.showLoading = showLoading;
window.hideLoading = hideLoading;
window.setLanguage = setLanguage;
window.focusOnBranch = focusOnBranch;
window.DeviceCapabilities = DeviceCapabilities;