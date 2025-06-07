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
        console.log('Kapital Bank AI Assistant initializing...');
        
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
        
        console.log('Kapital Bank AI Assistant ready!');
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
            ratesHTML += `
                <div class="currency-item mb-2" data-currency="${code}">
                    <div class="d-flex justify-content-between align-items-center">
                        <div class="d-flex align-items-center">
                            <span class="currency-flag me-2">${this.getCurrencyFlag(code)}</span>
                            <div>
                                <span class="currency-code fw-bold">${code}</span>
                                <div class="small text-muted">${data.name}</div>
                            </div>
                        </div>
                        <div class="text-end">
                            <span class="currency-rate fw-bold">${data.rate} AZN</span>
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
        const resultDiv = document.getElementById('conversionResult');
        
        // Populate currency selects
        this.populateCurrencySelects();
        
        // Auto-convert on input change
        [amountInput, fromSelect, toSelect].forEach(input => {
            if (input) {
                input.addEventListener('input', () => this.performConversion());
            }
        });
        
        // Initial conversion
        this.performConversion();
    }
    
    async performConversion() {
        const amount = parseFloat(document.getElementById('amount')?.value || 0);
        const fromCurrency = document.getElementById('fromCurrency')?.value;
        const toCurrency = document.getElementById('toCurrency')?.value;
        const resultDiv = document.getElementById('conversionResult');
        
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
            resultDiv.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    Conversion failed. Please try again.
                </div>
            `;
        }
    }
    
    convertOffline(amount, fromCurrency, toCurrency) {
        if (!this.currency.rates) {
            throw new Error('No cached rates available');
        }
        
        const fromRate = fromCurrency === 'AZN' ? 1 : this.currency.rates[fromCurrency]?.rate;
        const toRate = toCurrency === 'AZN' ? 1 : this.currency.rates[toCurrency]?.rate;
        
        if (!fromRate || !toRate) {
            throw new Error('Currency not supported');
        }
        
        const aznAmount = amount / fromRate;
        const convertedAmount = aznAmount * toRate;
        
        return {
            from_currency: fromCurrency,
            to_currency: toCurrency,
            from_amount: amount,
            to_amount: convertedAmount,
            exchange_rate: toRate / fromRate,
            source: this.currency.source + ' (Offline)',
            disclaimer: 'Offline calculation using cached rates',
            timestamp: new Date().toISOString()
        };
    }
    
    displayConversionResult(result, container) {
        const isOffline = result.source?.includes('Offline') || !this.isOnline;
        
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
    
    // Location Functions
    async loadLocations(filters = {}) {
        try {
            const params = new URLSearchParams();
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
        const container = document.getElementById('locationsList');
        if (!container || !this.locations.data) return;
        
        let locationsHTML = '';
        
        this.locations.data.forEach(location => {
            const distanceText = location.distance ? 
                `<span class="location-distance">${location.distance} km</span>` : '';
            
            locationsHTML += `
                <div class="location-item" data-location-id="${location.id}">
                    <div class="d-flex justify-content-between">
                        <div class="flex-grow-1">
                            <div class="location-name">${location.name}</div>
                            <div class="location-address">${location.address}</div>
                            <div class="mt-2">
                                <span class="location-type ${location.type}">${location.type.toUpperCase()}</span>
                                ${location.phone ? `<span class="ms-2"><i class="bi bi-telephone me-1"></i>${location.phone}</span>` : ''}
                            </div>
                            <div class="small text-muted mt-1">
                                <i class="bi bi-clock me-1"></i>${location.hours}
                            </div>
                        </div>
                        <div class="text-end">
                            ${distanceText}
                            <div class="mt-2">
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
            `;
        });
        
        container.innerHTML = locationsHTML || '<div class="text-center text-muted py-4">No locations found</div>';
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
            this.addChatMessage('ai', response.response);
            
        } catch (error) {
            console.error('Chat error:', error);
            this.hideTypingIndicator();
            
            // Offline response
            const offlineResponse = this.generateOfflineChatResponse(message);
            this.addChatMessage('ai', offlineResponse);
        }
        
        // Save chat history
        this.saveChatHistory();
    }
    
    addChatMessage(sender, content) {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-${sender}`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.textContent = content;
        
        messageDiv.appendChild(messageContent);
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
    
    generateOfflineChatResponse(message) {
        const msg = message.toLowerCase();
        
        if (msg.includes('currency') || msg.includes('exchange') || msg.includes('rate')) {
            return "I can help with currency information! However, I'm currently offline so I can't provide live rates. You can use the offline currency converter on the currency page with cached CBAR rates.";
        } else if (msg.includes('location') || msg.includes('branch') || msg.includes('atm')) {
            return "I'd love to help you find branches and ATMs! Unfortunately, location services require an internet connection. Please try again when you're back online, or call our customer service at +994 12 310 00 00.";
        } else if (msg.includes('loan') || msg.includes('credit')) {
            return "I can provide general loan information! You can use the offline loan calculator on our loans page. For specific rates and applications, please visit a branch or contact us at +994 12 310 00 00.";
        } else {
            return "I'm currently offline, so my responses are limited. For immediate assistance, please call our customer service at +994 12 310 00 00 or visit any Kapital Bank branch. I'll be back with full functionality once you're online!";
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
            localStorage.setItem('kb_chat_history', JSON.stringify(this.chat.messages));
        } catch (error) {
            console.warn('Failed to save chat history:', error);
        }
    }
    
    displayChatHistory() {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages || !this.chat.messages.length) return;
        
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
        }
    }
    
    showTypingIndicator() {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) return;
        
        const typingDiv = document.createElement('div');
        typingDiv.className = 'typing-indicator';
        typingDiv.id = 'typingIndicator';
        typingDiv.innerHTML = `
            <div class="typing-content">
                <span>AI is typing</span>
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
                Install Kapital Bank AI Assistant for easy access!
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
    
    loadQuickStats() {
        // Mock implementation for quick stats on home page
        console.log('Loading quick stats...');
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
                attribution: ' OpenStreetMap contributors'
            }).addTo(this.state.map);
            
            // Add user location marker
            L.marker(this.state.currentLocation)
                .addTo(this.state.map)
                .bindPopup('Your location')
                .openPopup();
                
        } catch (error) {
            console.error('Map initialization error:', error);
        }
    }
    
    updateMapMarkers() {
        if (!this.state.map || !this.locations.data) return;
        
        // Clear existing markers (except user location)
        // Implementation would go here
    }
    
    setupLocationFilters() {
        const filterForm = document.getElementById('locationSearchForm');
        if (filterForm) {
            filterForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const formData = new FormData(filterForm);
                const filters = Object.fromEntries(formData);
                this.loadLocations(filters);
            });
        }
    }
    
    requestUserLocation() {
        if (!navigator.geolocation) return;
        
        navigator.geolocation.getCurrentPosition(
            (position) => {
                this.state.currentLocation = [
                    position.coords.latitude,
                    position.coords.longitude
                ];
                this.locations.userLocation = this.state.currentLocation;
                
                if (this.state.map) {
                    this.state.map.setView(this.state.currentLocation, 14);
                }
            },
            (error) => {
                console.warn('Geolocation error:', error);
            }
        );
    }
    
    setupLoanCalculator() {
        // Implementation for loan calculator
        console.log('Setting up loan calculator...');
    }
    
    populateCurrencySelects() {
        const fromSelect = document.getElementById('fromCurrency');
        const toSelect = document.getElementById('toCurrency');
        
        if (!fromSelect || !toSelect || !this.currency.rates) return;
        
        const currencies = ['AZN', ...Object.keys(this.currency.rates)];
        
        currencies.forEach(currency => {
            const optionFrom = new Option(
                `${this.getCurrencyFlag(currency)} ${currency}`,
                currency
            );
            const optionTo = new Option(
                `${this.getCurrencyFlag(currency)} ${currency}`,
                currency
            );
            
            fromSelect.appendChild(optionFrom);
            toSelect.appendChild(optionTo);
        });
    }
    
    showLocationDetails(locationId) {
        console.log('Showing details for location:', locationId);
        // Implementation for showing location details
    }
    
    getDirections(lat, lng) {
        // Open directions in default map app
        const url = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`;
        window.open(url, '_blank');
    }
    
    handleLanguageChange(language) {
        console.log('Language changed to:', language);
        // Implementation for language change handling
    }
    
    handleAjaxForm(form) {
        console.log('Handling AJAX form:', form);
        // Implementation for AJAX form handling
    }
    
    handleAction(action, element) {
        console.log('Handling action:', action, element);
        // Implementation for action handling
    }
    
    saveFormData(input) {
        // Implementation for auto-saving form data
        try {
            const key = `form_${input.name}`;
            localStorage.setItem(key, input.value);
        } catch (error) {
            console.warn('Failed to save form data:', error);
        }
    }
    
    syncPendingData() {
        // Implementation for syncing pending data when back online
        console.log('Syncing pending data...');
    }
    
    updateCachedData() {
        // Implementation for updating cached data
        if (this.isOnline) {
            this.loadCurrencyRates();
            this.loadLocations();
        }
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