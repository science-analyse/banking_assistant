/**
 * Banking AI Assistant - Main Application Script
 * Fixed API calls and currency conversion
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
        console.log('Banking AI Assistant initializing...');
        
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
        
        console.log('Banking AI Assistant ready!');
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
    }
    
    // Initialize PWA features
    initPWA() {
        // Register service worker
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/static/sw.js')
                .then(registration => {
                    console.log('SW registered:', registration);
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
            this.updateCachedData();
        } else {
            if (statusIndicator) {
                statusIndicator.classList.remove('d-none');
                statusIndicator.classList.add('show');
            }
        }
        
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
        }
    }
    
    // Initialize home page
    initHomePage() {
        this.loadCurrencyRates();
        
        // Auto-refresh rates every 5 minutes
        setInterval(() => {
            if (this.isOnline) {
                this.loadCurrencyRates();
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
        this.requestUserLocation();
    }
    
    // Initialize chat page
    initChatPage() {
        this.loadChatHistory();
        this.setupChatInterface();
    }
    
    // Currency Rate Functions
    async loadCurrencyRates() {
        try {
            const response = await this.apiCall('/api/currency/rates');
            this.currency.rates = response.rates;
            this.currency.lastUpdated = response.last_updated;
            this.currency.source = response.source;
            
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
            this.updateCurrencyDisplay();
        }
    }
    
    updateCurrencyDisplay() {
        const ratesContainer = document.getElementById('currencyRates') || document.getElementById('officialRates');
        if (!ratesContainer || !this.currency.rates) return;
        
        let ratesHTML = '';
        
        Object.entries(this.currency.rates).forEach(([code, rate]) => {
            ratesHTML += `
                <div class="currency-item mb-2" data-currency="${code}">
                    <div class="d-flex justify-content-between align-items-center">
                        <div class="d-flex align-items-center">
                            <span class="currency-flag me-2">${this.getCurrencyFlag(code)}</span>
                            <div>
                                <span class="currency-code fw-bold">${code}</span>
                                <div class="small text-muted">${this.getCurrencyName(code)}</div>
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
            const isOffline = !this.isOnline || this.currency.source?.includes('Fallback');
            sourceInfo.innerHTML = `
                <div class="d-flex align-items-center justify-content-between">
                    <div>
                        <small class="text-muted">
                            <i class="bi bi-info-circle me-1"></i>
                            Source: ${this.currency.source || 'CBAR'}
                        </small>
                        ${isOffline ? '<br><small class="text-warning"><i class="bi bi-wifi-off me-1"></i>Offline data</small>' : ''}
                    </div>
                    <small class="text-muted">
                        Updated: ${this.formatDate(this.currency.lastUpdated)}
                    </small>
                </div>
            `;
        }
        
        // Update last update time
        const lastUpdateElement = document.getElementById('lastUpdateTime');
        if (lastUpdateElement) {
            lastUpdateElement.textContent = this.formatDate(this.currency.lastUpdated);
        }
    }
    
    // Currency converter
    initCurrencyConverter() {
        const converterForm = document.getElementById('currencyConverter');
        if (!converterForm) return;
        
        const amountInput = converterForm.querySelector('#amount');
        const fromSelect = converterForm.querySelector('#fromCurrency');
        const toSelect = converterForm.querySelector('#toCurrency');
        
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
        
        const fromRate = fromCurrency === 'AZN' ? 1 : this.currency.rates[fromCurrency];
        const toRate = toCurrency === 'AZN' ? 1 : this.currency.rates[toCurrency];
        
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
            return "I'd love to help you find branches and ATMs! Unfortunately, location services require an internet connection. Please try again when you're back online.";
        } else {
            return "I'm currently offline, so my responses are limited. For immediate assistance, please call customer service or visit any branch. I'll be back with full functionality once you're online!";
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
    
    // Missing implementations
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
            localStorage.setItem('kb_chat_history', JSON.stringify(this.chat.messages.slice(-50)));
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
        // Implementation for PWA install prompt
        console.log('Install prompt available');
    }
    
    initMap() {
        const mapContainer = document.getElementById('map');
        if (!mapContainer || typeof L === 'undefined') return;
        
        try {
            this.state.map = L.map('map').setView(this.state.currentLocation, 12);
            
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }).addTo(this.state.map);
            
        } catch (error) {
            console.error('Map initialization error:', error);
        }
    }
    
    updateMapMarkers() {
        // Implementation for updating map markers
        if (!this.state.map || !this.locations.data) return;
        console.log('Updating map markers for', this.locations.data.length, 'locations');
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
            }
        );
    }
    
    showLocationDetails(locationId) {
        console.log('Showing details for location:', locationId);
    }
    
    getDirections(lat, lng) {
        const url = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`;
        window.open(url, '_blank');
    }
    
    handleLanguageChange(language) {
        console.log('Language changed to:', language);
    }
    
    handleAjaxForm(form) {
        console.log('Handling AJAX form:', form);
    }
    
    handleAction(action, element) {
        console.log('Handling action:', action, element);
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
    
    updateCachedData() {
        if (this.isOnline) {
            this.loadCurrencyRates();
            this.loadLocations();
        }
    }
}

// Initialize the app when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.app = new KapitalBankApp();
});
