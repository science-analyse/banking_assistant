/**
 * AI Assistant - Main Application Script
 * Light Mode Only - Enhanced with PWA and offline support
 */

class KapitalBankApp {
    constructor() {
        this.isOnline = navigator.onLine;
        this.apiBaseUrl = '';
        this.currency = {
            rates: null,
            lastUpdated: null
        };
        this.locations = {
            data: null,
            userLocation: null
        };
        this.chat = {
            messages: [],
            sessionId: this.generateSessionId()
        };
        this.state = {
            map: null,
            currentLocation: [40.4093, 49.8671] // Default Baku coordinates
        };
        this.deferredPrompt = null;
        
        this.init();
    }
    
    // Initialize the application
    init() {
        console.log('AI Assistant initializing...');
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Initialize PWA features
        this.initPWA();
        
        // Load cached data
        this.loadCachedData();
        
        // Initialize page-specific features
        this.initPageFeatures();
        
        // Setup connection monitoring
        this.setupConnectionMonitoring();
        
        console.log('AI Assistant ready!');
    }
    
    // Generate session ID
    generateSessionId() {
        return 'kb_session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    // Setup global event listeners
    setupEventListeners() {
        // Language change
        document.addEventListener('languageChanged', (e) => {
            this.handleLanguageChange(e.detail.language);
        });
        
        // Form submissions
        document.addEventListener('submit', (e) => {
            if (e.target.dataset.ajaxForm) {
                e.preventDefault();
                this.handleAjaxForm(e.target);
            }
        });
        
        // Click handlers for dynamic content
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-action]')) {
                this.handleAction(e.target.dataset.action, e.target);
            }
        });
        
        // Auto-save form data
        document.addEventListener('input', (e) => {
            if (e.target.matches('[data-autosave]')) {
                this.saveFormData(e.target);
            }
        });
    }
    
    // Initialize PWA features
    initPWA() {
        // Register service worker
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/static/sw.js')
                .then(registration => {
                    console.log('SW registered:', registration);
                    
                    // Handle service worker updates
                    registration.addEventListener('updatefound', () => {
                        const newWorker = registration.installing;
                        newWorker.addEventListener('statechange', () => {
                            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                                this.showUpdateAvailable();
                            }
                        });
                    });
                })
                .catch(error => {
                    console.log('SW registration failed:', error);
                });
        }
        
        // Handle app install prompt
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            this.deferredPrompt = e;
            this.showInstallPrompt();
        });
        
        // Handle app installed
        window.addEventListener('appinstalled', () => {
            console.log('PWA installed');
            this.hideInstallPrompt();
        });
    }
    
    // Setup connection monitoring
    setupConnectionMonitoring() {
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.handleConnectionChange();
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.handleConnectionChange();
        });
        
        // Initial connection check
        this.handleConnectionChange();
    }
    
    // Handle connection state changes
    handleConnectionChange() {
        const statusIndicator = document.getElementById('connectionStatus');
        
        if (this.isOnline) {
            if (statusIndicator && !statusIndicator.classList.contains('d-none')) {
                statusIndicator.classList.add('d-none');
            }
            
            // Sync any pending data when coming back online
            this.syncPendingData();
            
            // Update cached data
            this.updateCachedData();
            
        } else {
            if (statusIndicator) {
                statusIndicator.classList.remove('d-none');
                statusIndicator.classList.add('show');
            }
        }
        
        // Update UI elements based on connection status
        this.updateUIForConnection();
    }
    
    // Update UI elements based on connection status
    updateUIForConnection() {
        const onlineElements = document.querySelectorAll('[data-requires-online]');
        const offlineElements = document.querySelectorAll('[data-offline-only]');
        
        onlineElements.forEach(el => {
            if (this.isOnline) {
                el.classList.remove('disabled');
                el.removeAttribute('disabled');
            } else {
                el.classList.add('disabled');
                el.setAttribute('disabled', 'true');
            }
        });
        
        offlineElements.forEach(el => {
            el.style.display = this.isOnline ? 'none' : 'block';
        });
    }
    
    // Load cached data
    loadCachedData() {
        this.loadCachedCurrencyRates();
        this.loadCachedLocations();
        this.loadChatHistory();
    }
    
    // Initialize page-specific features
    initPageFeatures() {
        const page = document.body.dataset.page;
        
        switch (page) {
            case 'home':
                this.initHomePage();
                break;
            case 'currency':
                this.initCurrencyPage();
                break;
            case 'locations':
                this.initLocationsPage();
                break;
            case 'chat':
                this.initChatPage();
                break;
            case 'loans':
                this.initLoansPage();
                break;
        }
    }
    
    // Initialize home page
    initHomePage() {
        this.loadQuickStats();
        this.loadRecentRates();
        
        // Auto-refresh stats every 5 minutes
        setInterval(() => {
            if (this.isOnline) {
                this.loadQuickStats();
                this.loadRecentRates();
            }
        }, 300000);
    }
    
    // Initialize currency page
    initCurrencyPage() {
        this.loadCurrencyRates();
        this.initCurrencyConverter();
        
        // Auto-refresh rates every 2 minutes
        setInterval(() => {
            if (this.isOnline) {
                this.loadCurrencyRates();
            }
        }, 120000);
    }
    
    // Initialize locations page
    initLocationsPage() {
        this.initMap();
        this.loadLocations();
        this.setupLocationFilters();
        
        // Request user location
        this.requestUserLocation();
    }
    
    // Initialize chat page
    initChatPage() {
        this.loadChatHistory();
        this.setupChatInterface();
    }
    
    // Initialize loans page
    initLoansPage() {
        this.setupLoanCalculator();
    }
    
    // Currency Rate Functions
    async loadCurrencyRates() {
        try {
            const response = await this.apiCall('/api/currency/rates');
            this.currency.rates = response.rates;
            this.currency.lastUpdated = response.last_updated;
            this.currency.source = response.source;
            this.currency.sourceNote = response.source_note;
            this.currency.disclaimer = response.disclaimer;
            
            this.updateCurrencyDisplay();
            this.cacheData('currency_rates', response);
            
        } catch (error) {
            console.error('Failed to load currency rates:', error);
            this.loadCachedCurrencyRates();
        }
    }
    
    loadCachedCurrencyRates() {
        const cached = this.getCachedData('currency_rates');
        if (cached) {
            this.currency.rates = cached.rates;
            this.currency.lastUpdated = cached.last_updated;
            this.currency.source = cached.source;
            this.currency.sourceNote = cached.source_note;
            this.currency.disclaimer = cached.disclaimer;
            this.updateCurrencyDisplay();
        }
    }
    
    updateCurrencyDisplay() {
        const ratesContainer = document.getElementById('currencyRates');
        if (!ratesContainer || !this.currency.rates) return;
        
        let ratesHTML = '';
        
        Object.entries(this.currency.rates).forEach(([code, data]) => {
            const rate = typeof data === 'object' ? data.rate : data;
            const name = typeof data === 'object' ? data.name : this.getCurrencyName(code);
            
            ratesHTML += `
                <div class="currency-item mb-2" data-currency="${code}">
                    <div class="d-flex justify-content-between align-items-center">
                        <div class="d-flex align-items-center">
                            <span class="currency-flag me-2">${this.getCurrencyFlag(code)}</span>
                            <div>
                                <span class="currency-code fw-bold">${code}</span>
                                <div class="small text-muted">${name}</div>
                            </div>
                        </div>
                        <div class="text-end">
                            <span class="currency-rate fw-bold">${parseFloat(rate).toFixed(4)} AZN</span>
                            <div class="small text-muted">per 1 ${code}</div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        ratesContainer.innerHTML = ratesHTML;
        
        // Update source information
        const sourceInfo = document.getElementById('rateSource');
        if (sourceInfo) {
            const isOffline = !this.isOnline || this.currency.source?.includes('Cached');
            sourceInfo.innerHTML = `
                <div class="d-flex align-items-center justify-content-between">
                    <div>
                        <small class="text-muted">
                            <i class="bi bi-info-circle me-1"></i>
                            Source: ${this.currency.source || 'CBAR (Cached)'}
                        </small>
                        ${isOffline ? '<br><small class="text-warning"><i class="bi bi-wifi-off me-1"></i>Offline data</small>' : ''}
                    </div>
                    <small class="text-muted">
                        Updated: ${this.formatDate(this.currency.lastUpdated)}
                    </small>
                </div>
                ${this.currency.sourceNote ? `<div class="mt-2"><small class="text-muted">${this.currency.sourceNote}</small></div>` : ''}
                ${this.currency.disclaimer ? `<div class="mt-1"><small class="text-info">${this.currency.disclaimer}</small></div>` : ''}
            `;
        }
    }
    
    // Currency converter
    initCurrencyConverter() {
        const converterForm = document.getElementById('currencyConverter');
        if (!converterForm) return;
        
        const amountInput = converterForm.querySelector('#amount');
        const fromSelect = converterForm.querySelector('#fromCurrency');
        const toSelect = converterForm.querySelector('#toCurrency');
        
        // Populate currency selects
        this.populateCurrencySelects();
        
        // Auto-convert on input change
        [amountInput, fromSelect, toSelect].forEach(input => {
            if (input) {
                input.addEventListener('input', () => this.performConversion());
                input.addEventListener('change', () => this.performConversion());
            }
        });
        
        // Initial conversion
        setTimeout(() => this.performConversion(), 500);
    }
    
    async performConversion() {
        const amount = parseFloat(document.getElementById('amount')?.value || 0);
        const fromCurrency = document.getElementById('fromCurrency')?.value;
        const toCurrency = document.getElementById('toCurrency')?.value;
        const resultDiv = document.getElementById('conversionResult') || document.getElementById('convertedAmount');
        
        if (!amount || !fromCurrency || !toCurrency || !resultDiv) return;
        
        try {
            if (this.isOnline) {
                const response = await this.apiCall('/api/currency/compare', {
                    method: 'POST',
                    body: JSON.stringify({
                        from_currency: fromCurrency,
                        to_currency: toCurrency,
                        amount: amount
                    })
                });
                
                this.displayConversionResult(response, resultDiv);
            } else {
                // Offline conversion using cached rates
                const result = this.convertOffline(amount, fromCurrency, toCurrency);
                this.displayConversionResult(result, resultDiv);
            }
        } catch (error) {
            console.error('Conversion error:', error);
            if (resultDiv.tagName === 'INPUT') {
                resultDiv.value = 'Error';
            } else {
                resultDiv.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="bi bi-exclamation-triangle me-2"></i>
                        Conversion failed. Please try again.
                    </div>
                `;
            }
        }
    }
    
    convertOffline(amount, fromCurrency, toCurrency) {
        if (!this.currency.rates) {
            throw new Error('No cached rates available');
        }
        
        const fromRate = fromCurrency === 'AZN' ? 1 : 
            (typeof this.currency.rates[fromCurrency] === 'object' ? 
                this.currency.rates[fromCurrency].rate : this.currency.rates[fromCurrency]);
        const toRate = toCurrency === 'AZN' ? 1 : 
            (typeof this.currency.rates[toCurrency] === 'object' ? 
                this.currency.rates[toCurrency].rate : this.currency.rates[toCurrency]);
        
        if (!fromRate || !toRate) {
            throw new Error('Currency not supported');
        }
        
        const aznAmount = fromCurrency === 'AZN' ? amount : amount * fromRate;
        const convertedAmount = toCurrency === 'AZN' ? aznAmount : aznAmount / toRate;
        
        return {
            from_currency: fromCurrency,
            to_currency: toCurrency,
            from_amount: amount,
            to_amount: convertedAmount,
            exchange_rate: toRate / fromRate,
            source: (this.currency.source || 'CBAR') + ' (Offline)',
            disclaimer: 'Offline calculation using cached rates',
            timestamp: new Date().toISOString()
        };
    }
    
    displayConversionResult(result, container) {
        const isOffline = result.source?.includes('Offline') || !this.isOnline;
        
        // If container is an input field (simple converter)
        if (container.tagName === 'INPUT') {
            container.value = result.to_amount.toFixed(2);
            return;
        }
        
        // Full conversion result display
        container.innerHTML = `
            <div class="card border-primary">
                <div class="card-header bg-primary text-white">
                    <h5 class="mb-0">
                        <i class="bi bi-arrow-left-right me-2"></i>
                        Conversion Result
                        ${isOffline ? '<span class="badge bg-warning ms-2"><i class="bi bi-wifi-off me-1"></i>Offline</span>' : ''}
                    </h5>
                </div>
                <div class="card-body text-center">
                    <div class="row">
                        <div class="col-5">
                            <h4 class="text-primary">${result.from_amount} ${result.from_currency}</h4>
                        </div>
                        <div class="col-2 d-flex align-items-center justify-content-center">
                            <i class="bi bi-arrow-right text-muted" style="font-size: 1.5rem;"></i>
                        </div>
                        <div class="col-5">
                            <h4 class="text-success">${result.to_amount.toFixed(2)} ${result.to_currency}</h4>
                        </div>
                    </div>
                    <div class="mt-3">
                        <small class="text-muted">
                            Exchange Rate: 1 ${result.from_currency} = ${result.exchange_rate.toFixed(4)} ${result.to_currency}
                        </small>
                    </div>
                    <div class="mt-2">
                        <small class="text-muted">
                            <i class="bi bi-clock me-1"></i>
                            ${this.formatDate(result.timestamp)}
                        </small>
                    </div>
                    ${result.disclaimer ? `<div class="mt-2"><small class="text-info">${result.disclaimer}</small></div>` : ''}
                </div>
            </div>
        `;
    }
    
    // Chat Functions
    async sendChatMessage(message) {
        if (!message.trim()) return;
        
        // Add user message to chat
        this.addChatMessage('user', message);
        
        // Show typing indicator
        this.showTypingIndicator();
        
        try {
            const response = await this.apiCall('/api/chat', {
                method: 'POST',
                body: JSON.stringify({
                    message: message,
                    session_id: this.chat.sessionId
                })
            });
            
            // Remove typing indicator
            this.hideTypingIndicator();
            
            // Add AI response
            this.addChatMessage('assistant', response.response);
            
        } catch (error) {
            console.error('Chat error:', error);
            this.hideTypingIndicator();
            
            // Offline response
            const offlineResponse = this.generateOfflineChatResponse(message);
            this.addChatMessage('assistant', offlineResponse);
        }
        
        // Save chat history
        this.saveChatHistory();
    }
    
    addChatMessage(sender, content) {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${sender} fade-in`;
        
        const messageTime = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        
        messageDiv.innerHTML = `
            <div class="d-flex justify-content-between align-items-start mb-1">
                <strong>${sender === 'user' ? 'You' : 'AI Assistant'}</strong>
                <small class="opacity-75">${messageTime}</small>
            </div>
            <div>${this.formatMessage(content)}</div>
        `;
        
        chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // Add to messages array
        this.chat.messages.push({
            sender: sender,
            content: content,
            timestamp: new Date().toISOString()
        });
    }
    
    formatMessage(content) {
        // Convert markdown-style formatting to HTML
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/```(.*?)```/gs, '<pre><code>$1</code></pre>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }
    
    generateOfflineChatResponse(message) {
        const msg = message.toLowerCase();
        
        if (msg.includes('currency') || msg.includes('exchange') || msg.includes('rate')) {
            return "I can help with currency information! However, I'm currently offline so I can't provide live rates. You can use the offline currency converter on the currency page with cached CBAR rates.";
        } else if (msg.includes('location') || msg.includes('branch') || msg.includes('atm')) {
            return "I'd love to help you find branches and ATMs! Unfortunately, location services require an internet connection. Please try again when you're back online, or call our customer service at +994 12 310 00 00.";
        } else if (msg.includes('loan') || msg.includes('credit')) {
            return "I can provide general loan information! You can use the offline loan calculator on our loans page. For specific rates and applications, please visit a branch or contact us at +994 12 310 00 00.";
        } else {
            return "I'm currently offline, so my responses are limited. For immediate assistance, please call our customer service at +994 12 310 00 00 or visit any branch. I'll be back with full functionality once you're online!";
        }
    }
    
    // Location Functions
    async loadLocations(filters = {}) {
        try {
            const params = new URLSearchParams();
            
            // Add user location if available
            if (this.locations.userLocation) {
                params.append('lat', this.locations.userLocation[0]);
                params.append('lon', this.locations.userLocation[1]);
            }
            
            // Add filters
            Object.entries(filters).forEach(([key, value]) => {
                if (value) params.append(key, value);
            });
            
            const response = await this.apiCall(`/api/locations?${params}`);
            this.locations.data = response.locations;
            
            this.updateLocationsDisplay();
            this.updateMapMarkers();
            this.cacheData('locations', response);
            
        } catch (error) {
            console.error('Failed to load locations:', error);
            this.loadCachedLocations();
        }
    }
    
    loadCachedLocations() {
        const cached = this.getCachedData('locations');
        if (cached) {
            this.locations.data = cached.locations;
            this.updateLocationsDisplay();
            this.updateMapMarkers();
        }
    }
    
    updateLocationsDisplay() {
        const container = document.getElementById('searchResults') || document.getElementById('locationsList');
        if (!container || !this.locations.data) return;
        
        let locationsHTML = '';
        
        this.locations.data.forEach(location => {
            const distanceText = location.distance ? 
                `<span class="location-distance badge bg-primary">${location.distance} km</span>` : '';
            
            locationsHTML += `
                <div class="location-item card mb-3" data-location-id="${location.id}">
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <div class="flex-grow-1">
                                <h6 class="location-name card-title">${location.name}</h6>
                                <p class="location-address text-muted">${location.address}</p>
                                <div class="mb-2">
                                    <span class="location-type badge bg-secondary">${location.type.toUpperCase()}</span>
                                    ${location.phone ? `<span class="ms-2 small"><i class="bi bi-telephone me-1"></i>${location.phone}</span>` : ''}
                                    ${distanceText}
                                </div>
                                <div class="small text-muted">
                                    <i class="bi bi-clock me-1"></i>${location.hours}
                                </div>
                            </div>
                            <div class="text-end">
                                <div class="btn-group-vertical">
                                    <button class="btn btn-sm btn-outline-primary" onclick="app.showLocationDetails('${location.id}')">
                                        <i class="bi bi-info-circle"></i>
                                    </button>
                                    <button class="btn btn-sm btn-primary" onclick="app.getDirections(${location.latitude}, ${location.longitude})">
                                        <i class="bi bi-navigation"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        container.innerHTML = locationsHTML || '<div class="text-center text-muted py-4">No locations found</div>';
    }
    
    // Utility Functions
    async apiCall(endpoint, options = {}) {
        const url = this.apiBaseUrl + endpoint;
        const defaultOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            ...options
        };
        
        if (!this.isOnline) {
            throw new Error('No internet connection');
        }
        
        const response = await fetch(url, defaultOptions);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return response.json();
    }
    
    // Cache management
    cacheData(key, data) {
        try {
            const cacheData = {
                data: data,
                timestamp: Date.now()
            };
            localStorage.setItem(`kb_cache_${key}`, JSON.stringify(cacheData));
        } catch (error) {
            console.warn('Failed to cache data:', error);
        }
    }
    
    getCachedData(key) {
        try {
            const cached = localStorage.getItem(`kb_cache_${key}`);
            if (cached) {
                const parsedData = JSON.parse(cached);
                // Check if cache is still valid (1 hour)
                if (Date.now() - parsedData.timestamp < 3600000) {
                    return parsedData.data;
                }
            }
        } catch (error) {
            console.warn('Failed to get cached data:', error);
        }
        return null;
    }
    
    // Helper methods
    getCurrencyFlag(code) {
        const flags = {
            'USD': '🇺🇸',
            'EUR': '🇪🇺', 
            'GBP': '🇬🇧',
            'RUB': '🇷🇺',
            'TRY': '🇹🇷',
            'GEL': '🇬🇪',
            'AZN': '🇦🇿'
        };
        return flags[code] || '💱';
    }
    
    getCurrencyName(code) {
        const names = {
            'USD': 'US Dollar',
            'EUR': 'Euro',
            'GBP': 'British Pound',
            'RUB': 'Russian Ruble',
            'TRY': 'Turkish Lira',
            'GEL': 'Georgian Lari',
            'AZN': 'Azerbaijani Manat'
        };
        return names[code] || code;
    }
    
    formatDate(dateString) {
        if (!dateString) return 'Unknown';
        try {
            return new Date(dateString).toLocaleString();
        } catch {
            return dateString;
        }
    }
    
    showAlert(html) {
        const container = document.getElementById('alertContainer');
        if (container) {
            container.insertAdjacentHTML('beforeend', html);
        }
    }
    
    // Missing implementations that were causing errors
    loadChatHistory() {
        try {
            const history = localStorage.getItem('kb_chat_history');
            if (history) {
                this.chat.messages = JSON.parse(history);
                this.displayChatHistory();
            }
        } catch (error) {
            console.warn('Failed to load chat history:', error);
            this.chat.messages = [];
        }
    }
    
    saveChatHistory() {
        try {
            localStorage.setItem('kb_chat_history', JSON.stringify(this.chat.messages.slice(-50))); // Keep last 50 messages
        } catch (error) {
            console.warn('Failed to save chat history:', error);
        }
    }
    
    displayChatHistory() {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages || !this.chat.messages.length) return;
        
        // Clear existing messages except welcome message
        const welcomeMsg = chatMessages.querySelector('.chat-message.assistant');
        chatMessages.innerHTML = '';
        if (welcomeMsg) {
            chatMessages.appendChild(welcomeMsg);
        }
        
        this.chat.messages.forEach(msg => {
            this.addChatMessage(msg.sender, msg.content);
        });
    }
    
    setupChatInterface() {
        const chatForm = document.getElementById('chatForm');
        const messageInput = document.getElementById('messageInput');
        
        if (chatForm && messageInput) {
            chatForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const message = messageInput.value.trim();
                if (message) {
                    this.sendChatMessage(message);
                    messageInput.value = '';
                }
            });
            
            // Handle Enter key (but allow Shift+Enter for new lines)
            messageInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    chatForm.dispatchEvent(new Event('submit'));
                }
            });
        }
    }
    
    showTypingIndicator() {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) return;
        
        const typingDiv = document.createElement('div');
        typingDiv.className = 'chat-message assistant typing-indicator';
        typingDiv.id = 'typingIndicator';
        typingDiv.innerHTML = `
            <div class="d-flex justify-content-between align-items-start mb-1">
                <strong>AI Assistant</strong>
                <small class="opacity-75">now</small>
            </div>
            <div class="typing-content">
                <span>typing</span>
                <div class="typing-dots">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        
        chatMessages.appendChild(typingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    hideTypingIndicator() {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) {
            indicator.remove();
        }
    }
    
    showInstallPrompt() {
        if (!this.deferredPrompt) return;
        
        const alertHTML = `
            <div class="alert alert-info alert-dismissible fade show" role="alert" id="installPrompt">
                <i class="bi bi-download me-2"></i>
                Install AI Assistant for easy access!
                <button type="button" class="btn btn-sm btn-outline-info ms-2" onclick="app.installApp()">Install</button>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        this.showAlert(alertHTML);
    }
    
    hideInstallPrompt() {
        const prompt = document.getElementById('installPrompt');
        if (prompt) {
            prompt.remove();
        }
        this.deferredPrompt = null;
    }
    
    async installApp() {
        if (!this.deferredPrompt) return;
        
        try {
            const result = await this.deferredPrompt.prompt();
            console.log('Install prompt result:', result);
            this.hideInstallPrompt();
        } catch (error) {
            console.error('Install prompt error:', error);
        }
        
        this.deferredPrompt = null;
    }
    
    showUpdateAvailable() {
        const alertHTML = `
            <div class="alert alert-success alert-dismissible fade show" role="alert" id="updatePrompt">
                <i class="bi bi-arrow-clockwise me-2"></i>
                A new version is available! 
                <button type="button" class="btn btn-sm btn-outline-success ms-2" onclick="window.location.reload()">Update Now</button>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        this.showAlert(alertHTML);
    }
    
    loadQuickStats() {
        // Mock implementation for quick stats on home page
        console.log('Loading quick stats...');
        // You could add actual stats loading here
    }
    
    loadRecentRates() {
        // Implementation for loading recent rates on home page
        this.loadCurrencyRates();
    }
    
    initMap() {
        const mapContainer = document.getElementById('map');
        if (!mapContainer || typeof L === 'undefined') return;
        
        try {
            this.state.map = L.map('map').setView(this.state.currentLocation, 12);
            
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }).addTo(this.state.map);
            
            // Add user location marker
            this.userMarker = L.marker(this.state.currentLocation, {
                icon: L.divIcon({
                    className: 'user-location-marker',
                    html: '<i class="bi bi-geo-alt-fill" style="color: #dc3545; font-size: 24px;"></i>',
                    iconSize: [24, 24],
                    iconAnchor: [12, 24]
                })
            }).addTo(this.state.map)
              .bindPopup('Your location')
              .openPopup();
                
        } catch (error) {
            console.error('Map initialization error:', error);
        }
    }
    
    updateMapMarkers() {
        if (!this.state.map || !this.locations.data) return;
        
        // Clear existing location markers (keep user marker)
        if (this.locationMarkers) {
            this.locationMarkers.forEach(marker => this.state.map.removeLayer(marker));
        }
        this.locationMarkers = [];
        
        // Add location markers
        this.locations.data.forEach(location => {
            const icon = this.getLocationIcon(location.type);
            const marker = L.marker([location.latitude, location.longitude], { icon })
                .addTo(this.state.map)
                .bindPopup(`
                    <div class="location-popup">
                        <h6>${location.name}</h6>
                        <p class="small mb-1">${location.address}</p>
                        <p class="small mb-1"><i class="bi bi-clock me-1"></i>${location.hours}</p>
                        ${location.phone ? `<p class="small mb-1"><i class="bi bi-telephone me-1"></i>${location.phone}</p>` : ''}
                        <div class="mt-2">
                            <button class="btn btn-sm btn-primary" onclick="app.getDirections(${location.latitude}, ${location.longitude})">
                                <i class="bi bi-navigation me-1"></i>Directions
                            </button>
                        </div>
                    </div>
                `);
            
            this.locationMarkers.push(marker);
        });
        
        // Fit map to show all markers
        if (this.locations.data.length > 0) {
            const group = new L.featureGroup([...this.locationMarkers, this.userMarker]);
            this.state.map.fitBounds(group.getBounds().pad(0.1));
        }
    }
    
    getLocationIcon(type) {
        const icons = {
            'branch': '🏛️',
            'atm': '🏧',
            'cash_in': '💰',
            'digital_center': '💻',
            'payment_terminal': '💳'
        };
        
        return L.divIcon({
            className: 'location-marker',
            html: `<div style="background: white; border: 2px solid #1f4e79; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; font-size: 16px;">${icons[type] || '📍'}</div>`,
            iconSize: [30, 30],
            iconAnchor: [15, 15]
        });
    }
    
    setupLocationFilters() {
        const filterForm = document.getElementById('locationSearchForm');
        if (filterForm) {
            filterForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const formData = new FormData(filterForm);
                const filters = {
                    type: formData.get('serviceType'),
                    radius: parseFloat(formData.get('searchRadius'))
                };
                this.loadLocations(filters);
            });
        }
        
        // Quick search buttons
        document.querySelectorAll('[data-service-type]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const serviceType = e.target.closest('[data-service-type]').dataset.serviceType;
                document.getElementById('serviceType').value = serviceType;
                this.loadLocations({ type: serviceType });
            });
        });
    }
    
    requestUserLocation() {
        if (!navigator.geolocation) {
            console.warn('Geolocation not supported');
            return;
        }
        
        navigator.geolocation.getCurrentPosition(
            (position) => {
                this.state.currentLocation = [
                    position.coords.latitude,
                    position.coords.longitude
                ];
                this.locations.userLocation = this.state.currentLocation;
                
                if (this.state.map) {
                    this.state.map.setView(this.state.currentLocation, 14);
                    if (this.userMarker) {
                        this.userMarker.setLatLng(this.state.currentLocation);
                    }
                }
                
                // Update location display
                const locationDisplay = document.getElementById('userLocationDisplay');
                if (locationDisplay) {
                    locationDisplay.innerHTML = '<i class="bi bi-geo-alt-fill text-success me-1"></i>Location found';
                }
            },
            (error) => {
                console.warn('Geolocation error:', error);
                const locationDisplay = document.getElementById('userLocationDisplay');
                if (locationDisplay) {
                    locationDisplay.innerHTML = '<i class="bi bi-geo-alt text-warning me-1"></i>Using default location (Baku)';
                }
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 300000 // 5 minutes
            }
        );
    }
    
    setupLoanCalculator() {
        const calculatorInputs = ['loanAmount', 'interestRate', 'loanTerm'];
        
        calculatorInputs.forEach(inputId => {
            const input = document.getElementById(inputId);
            if (input) {
                input.addEventListener('input', () => {
                    clearTimeout(this.calculateTimeout);
                    this.calculateTimeout = setTimeout(() => this.calculateLoan(), 500);
                });
            }
        });
        
        // Initial calculation
        setTimeout(() => this.calculateLoan(), 1000);
    }
    
    calculateLoan() {
        const amount = parseFloat(document.getElementById('loanAmount')?.value || 0);
        const rate = parseFloat(document.getElementById('interestRate')?.value || 0) / 100 / 12;
        const term = parseFloat(document.getElementById('loanTerm')?.value || 0) * 12;
        const resultsDiv = document.getElementById('calculationResults');
        
        if (!amount || !rate || !term || !resultsDiv) return;
        
        try {
            const monthlyPayment = amount * (rate * Math.pow(1 + rate, term)) / (Math.pow(1 + rate, term) - 1);
            const totalPayment = monthlyPayment * term;
            const totalInterest = totalPayment - amount;
            
            const resultsHTML = `
                <div class="card border-primary">
                    <div class="card-header bg-primary text-white">
                        <h5 class="mb-0">
                            <i class="bi bi-calculator me-2"></i>
                            Calculation Results
                        </h5>
                    </div>
                    <div class="card-body">
                        <div class="row text-center mb-4">
                            <div class="col-12">
                                <h3 class="text-primary">${monthlyPayment.toFixed(2)} AZN</h3>
                                <p class="text-muted mb-0">Monthly Payment</p>
                            </div>
                        </div>
                        <div class="row text-center">
                            <div class="col-4">
                                <div class="fw-bold">${amount.toFixed(2)} AZN</div>
                                <small class="text-muted">Loan Amount</small>
                            </div>
                            <div class="col-4">
                                <div class="fw-bold">${totalPayment.toFixed(2)} AZN</div>
                                <small class="text-muted">Total Payment</small>
                            </div>
                            <div class="col-4">
                                <div class="fw-bold">${totalInterest.toFixed(2)} AZN</div>
                                <small class="text-muted">Total Interest</small>
                            </div>
                        </div>
                        
                        <div class="mt-4">
                            <h6>Payment Breakdown</h6>
                            <div class="progress mb-2">
                                <div class="progress-bar bg-primary" style="width: ${(amount/totalPayment*100).toFixed(1)}%"></div>
                                <div class="progress-bar bg-warning" style="width: ${(totalInterest/totalPayment*100).toFixed(1)}%"></div>
                            </div>
                            <div class="row">
                                <div class="col-6">
                                    <small><span class="badge bg-primary me-1"></span>Principal: ${((amount/totalPayment)*100).toFixed(1)}%</small>
                                </div>
                                <div class="col-6">
                                    <small><span class="badge bg-warning me-1"></span>Interest: ${((totalInterest/totalPayment)*100).toFixed(1)}%</small>
                                </div>
                            </div>
                        </div>
                        
                        <div class="mt-4 text-center">
                            <small class="text-muted">
                                <i class="bi bi-info-circle me-1"></i>
                                These are estimated calculations. Actual rates and terms may vary.
                            </small>
                        </div>
                    </div>
                </div>
            `;
            
            resultsDiv.innerHTML = resultsHTML;
        } catch (error) {
            resultsDiv.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    Please enter valid values for all fields.
                </div>
            `;
        }
    }
    
    populateCurrencySelects() {
        const fromSelect = document.getElementById('fromCurrency');
        const toSelect = document.getElementById('toCurrency');
        
        if (!fromSelect || !toSelect) return;
        
        // Clear existing options (except default ones)
        const currencies = ['AZN', 'USD', 'EUR', 'GBP', 'RUB', 'TRY', 'GEL'];
        
        // Add currencies from rates if available
        if (this.currency.rates) {
            Object.keys(this.currency.rates).forEach(currency => {
                if (!currencies.includes(currency)) {
                    currencies.push(currency);
                }
            });
        }
        
        // Only populate if selects are empty or have few options
        if (fromSelect.options.length <= 1) {
            currencies.forEach(currency => {
                const optionFrom = new Option(
                    `${this.getCurrencyFlag(currency)} ${currency} - ${this.getCurrencyName(currency)}`,
                    currency
                );
                const optionTo = new Option(
                    `${this.getCurrencyFlag(currency)} ${currency} - ${this.getCurrencyName(currency)}`,
                    currency
                );
                
                fromSelect.appendChild(optionFrom);
                toSelect.appendChild(optionTo);
            });
        }
    }
    
    showLocationDetails(locationId) {
        console.log('Showing details for location:', locationId);
        // Implementation for showing location details in modal
        const location = this.locations.data?.find(loc => loc.id === locationId);
        if (!location) return;
        
        const modal = document.getElementById('locationDetailsModal');
        const content = document.getElementById('locationDetailsContent');
        
        if (modal && content) {
            content.innerHTML = `
                <div class="row">
                    <div class="col-md-6">
                        <h6><i class="bi bi-info-circle me-2"></i>Information</h6>
                        <p><strong>Type:</strong> ${location.type.toUpperCase()}</p>
                        <p><strong>Address:</strong> ${location.address}</p>
                        ${location.phone ? `<p><strong>Phone:</strong> ${location.phone}</p>` : ''}
                        ${location.distance ? `<p><strong>Distance:</strong> ${location.distance} km</p>` : ''}
                    </div>
                    <div class="col-md-6">
                        <h6><i class="bi bi-clock me-2"></i>Working Hours</h6>
                        <p>${location.hours}</p>
                    </div>
                </div>
                <hr>
                <h6><i class="bi bi-gear me-2"></i>Available Services</h6>
                <div class="row">
                    ${this.getServicesForLocationType(location.type)}
                </div>
            `;
            
            // Set up directions button
            const directionsBtn = document.getElementById('getDirectionsBtn');
            if (directionsBtn) {
                directionsBtn.onclick = () => this.getDirections(location.latitude, location.longitude);
            }
            
            const bootstrapModal = new bootstrap.Modal(modal);
            bootstrapModal.show();
        }
    }
    
    getServicesForLocationType(type) {
        const services = {
            'branch': ['Cash withdrawal', 'Deposits', 'Account opening', 'Loans', 'Currency exchange', 'Transfers'],
            'atm': ['Cash withdrawal', 'Balance inquiry', '24/7 access', 'Mini statements'],
            'cash_in': ['Cash deposits', 'Account funding', 'Quick deposits'],
            'digital_center': ['Self-service banking', 'Digital assistance', 'Account management'],
            'payment_terminal': ['Bill payments', 'Utility payments', 'Mobile top-up']
        };
        
        const serviceList = services[type] || [];
        return serviceList.map(service => 
            `<div class="col-md-6 mb-2"><i class="bi bi-check-circle text-success me-2"></i>${service}</div>`
        ).join('');
    }
    
    getDirections(lat, lng) {
        // Open directions in default map app
        const url = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`;
        window.open(url, '_blank');
    }
    
    handleLanguageChange(language) {
        console.log('Language changed to:', language);
        // Implementation for language change handling
        // You could reload content in the new language here
    }
    
    handleAjaxForm(form) {
        console.log('Handling AJAX form:', form);
        // Implementation for AJAX form handling
    }
    
    handleAction(action, element) {
        console.log('Handling action:', action, element);
        // Implementation for action handling based on data-action attributes
        switch (action) {
            case 'refresh-rates':
                this.loadCurrencyRates();
                break;
            case 'get-location':
                this.requestUserLocation();
                break;
            case 'clear-chat':
                this.clearChat();
                break;
            default:
                console.log('Unknown action:', action);
        }
    }
    
    clearChat() {
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            // Keep only the welcome message
            const welcomeMsg = chatMessages.querySelector('.chat-message.assistant');
            chatMessages.innerHTML = '';
            if (welcomeMsg) {
                chatMessages.appendChild(welcomeMsg);
            }
        }
        
        this.chat.messages = [];
        this.saveChatHistory();
    }
    
    saveFormData(input) {
        // Implementation for auto-saving form data
        try {
            const key = `form_${input.name || input.id}`;
            localStorage.setItem(key, input.value);
        } catch (error) {
            console.warn('Failed to save form data:', error);
        }
    }
    
    syncPendingData() {
        // Implementation for syncing pending data when back online
        console.log('Syncing pending data...');
        // You could implement offline form submissions sync here
    }
    
    updateCachedData() {
        // Implementation for updating cached data
        if (this.isOnline) {
            this.loadCurrencyRates();
            this.loadLocations();
        }
    }
}

// Global utility objects and functions
const Utils = {
    showAlert: function(type, message, duration = 5000) {
        const alertContainer = document.getElementById('alertContainer');
        if (!alertContainer) return;
        
        const alertId = 'alert_' + Date.now();
        const alertHTML = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert" id="${alertId}">
                <i class="bi bi-${type === 'success' ? 'check-circle' : type === 'danger' ? 'exclamation-triangle' : 'info-circle'} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        alertContainer.insertAdjacentHTML('beforeend', alertHTML);
        
        // Auto-dismiss
        if (duration > 0) {
            setTimeout(() => {
                const alert = document.getElementById(alertId);
                if (alert) {
                    alert.remove();
                }
            }, duration);
        }
    },
    
    formatCurrency: function(amount, currency = 'AZN') {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency,
            minimumFractionDigits: 2
        }).format(amount);
    },
    
    debounce: function(func, wait) {
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
};

const LocationService = {
    getCurrentLocation: function() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Geolocation not supported'));
                return;
            }
            
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    resolve([position.coords.latitude, position.coords.longitude]);
                },
                (error) => {
                    reject(error);
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 300000
                }
            );
        });
    }
};

const CurrencyService = {
    updateCurrencyDisplay: function(rates) {
        if (window.app) {
            window.app.currency.rates = rates;
            window.app.updateCurrencyDisplay();
        }
    }
};

const PageHandlers = {
    autoConvert: function() {
        if (window.app && window.app.performConversion) {
            window.app.performConversion();
        }
    },
    
    refreshCurrencyRates: async function() {
        if (window.app) {
            await window.app.loadCurrencyRates();
        }
    },
    
    searchServices: function(serviceType) {
        if (window.app) {
            window.app.loadLocations({ type: serviceType });
        }
    }
};

const ChatSystem = {
    sendSuggestion: function(suggestion) {
        const messageInput = document.getElementById('messageInput');
        if (messageInput) {
            messageInput.value = suggestion;
            const form = document.getElementById('chatForm');
            if (form) {
                form.dispatchEvent(new Event('submit'));
            }
        }
    }
};

// Global functions for backwards compatibility
function swapCurrencies() {
    const fromSelect = document.getElementById('fromCurrency');
    const toSelect = document.getElementById('toCurrency');
    
    if (fromSelect && toSelect) {
        const temp = fromSelect.value;
        fromSelect.value = toSelect.value;
        toSelect.value = temp;
        
        if (window.app && window.app.performConversion) {
            window.app.performConversion();
        }
    }
}

function quickConvert(amount, from, to) {
    const amountInput = document.getElementById('amount');
    const fromSelect = document.getElementById('fromCurrency');
    const toSelect = document.getElementById('toCurrency');
    
    if (amountInput) amountInput.value = amount;
    if (fromSelect) fromSelect.value = from;
    if (toSelect) toSelect.value = to;
    
    if (window.app && window.app.performConversion) {
        window.app.performConversion();
    }
}

function clearChat() {
    if (window.app && window.app.clearChat) {
        window.app.clearChat();
    }
}

// Initialize the app when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize the main app
    window.app = new KapitalBankApp();
    
    // Make app globally available for debugging
    if (typeof window !== 'undefined') {
        window.KapitalBankApp = KapitalBankApp;
        window.Utils = Utils;
        window.LocationService = LocationService;
        window.CurrencyService = CurrencyService;
        window.PageHandlers = PageHandlers;
        window.ChatSystem = ChatSystem;
    }
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        KapitalBankApp,
        Utils,
        LocationService,
        CurrencyService,
        PageHandlers,
        ChatSystem
    };
}