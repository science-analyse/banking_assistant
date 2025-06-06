/**
 * Kapital Bank AI Assistant - Simplified Frontend JavaScript
 * Connects to FastAPI backend with MCP integration
 */

// Global application state
window.KapitalBankApp = {
    config: {
        defaultLocation: [40.4093, 49.8671], // Baku center
        mapZoom: 12,
        searchRadius: 5,
        apiBaseUrl: window.location.origin,
        updateInterval: 300000, // 5 minutes
        debounceDelay: 300
    },
    
    state: {
        currentLocation: null,
        map: null,
        markers: [],
        currentLanguage: localStorage.getItem('language') || 'en',
        isOnline: navigator.onLine,
        lastUpdate: null
    },
    
    features: {
        geolocation: 'geolocation' in navigator,
        notifications: 'Notification' in window
    }
};

// Utility functions
const Utils = {
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
    },
    
    formatDistance(distance) {
        if (distance < 1) {
            return `${Math.round(distance * 1000)}m`;
        }
        return `${distance.toFixed(1)}km`;
    },
    
    formatCurrency(amount, currency = 'AZN', precision = 4) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency,
            minimumFractionDigits: precision,
            maximumFractionDigits: precision
        }).format(amount);
    },
    
    showLoading(message = 'Loading...') {
        const modal = new bootstrap.Modal(document.getElementById('loadingModal'));
        document.getElementById('loadingText').textContent = message;
        modal.show();
    },
    
    hideLoading() {
        const modal = bootstrap.Modal.getInstance(document.getElementById('loadingModal'));
        if (modal) modal.hide();
    },
    
    showAlert(type, message, duration = 5000) {
        const alertContainer = document.getElementById('alertContainer');
        if (!alertContainer) return;
        
        const alertId = 'alert-' + Date.now();
        const alertHTML = `
            <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
                <i class="bi bi-${this.getAlertIcon(type)} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        alertContainer.insertAdjacentHTML('beforeend', alertHTML);
        
        setTimeout(() => {
            const alert = document.getElementById(alertId);
            if (alert) {
                const bsAlert = bootstrap.Alert.getInstance(alert);
                if (bsAlert) bsAlert.close();
            }
        }, duration);
    },
    
    getAlertIcon(type) {
        const icons = {
            'success': 'check-circle',
            'error': 'exclamation-triangle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle',
            'danger': 'exclamation-triangle'
        };
        return icons[type] || 'info-circle';
    },
    
    async apiCall(endpoint, options = {}) {
        try {
            const response = await fetch(`${KapitalBankApp.config.apiBaseUrl}${endpoint}`, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error(`API call failed for ${endpoint}:`, error);
            throw error;
        }
    }
};

// Location Services
const LocationService = {
    async getCurrentLocation() {
        return new Promise((resolve, reject) => {
            if (!KapitalBankApp.features.geolocation) {
                reject(new Error('Geolocation not supported'));
                return;
            }
            
            navigator.geolocation.getCurrentPosition(
                position => {
                    const location = [position.coords.latitude, position.coords.longitude];
                    KapitalBankApp.state.currentLocation = location;
                    resolve(location);
                },
                error => {
                    console.warn('Geolocation error:', error);
                    const defaultLocation = KapitalBankApp.config.defaultLocation;
                    KapitalBankApp.state.currentLocation = defaultLocation;
                    resolve(defaultLocation);
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 300000
                }
            );
        });
    },
    
    async findNearbyServices(serviceType, location = null, radius = 5) {
        const searchLocation = location || KapitalBankApp.state.currentLocation || KapitalBankApp.config.defaultLocation;
        
        try {
            const result = await Utils.apiCall('/api/locations/find', {
                method: 'POST',
                body: JSON.stringify({
                    latitude: searchLocation[0],
                    longitude: searchLocation[1],
                    service_type: serviceType,
                    radius_km: radius,
                    limit: 20
                })
            });
            
            return result;
        } catch (error) {
            Utils.showAlert('error', `Failed to find ${serviceType} locations: ${error.message}`);
            return { locations: [], total_found: 0 };
        }
    }
};

// Map Management
const MapManager = {
    initMap(containerId, center = null) {
        const mapCenter = center || KapitalBankApp.state.currentLocation || KapitalBankApp.config.defaultLocation;
        
        const map = L.map(containerId).setView(mapCenter, KapitalBankApp.config.mapZoom);
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 18
        }).addTo(map);
        
        KapitalBankApp.state.map = map;
        return map;
    },
    
    addMarkers(locations, map = null) {
        const targetMap = map || KapitalBankApp.state.map;
        if (!targetMap) return;
        
        this.clearMarkers();
        
        const markers = [];
        
        locations.forEach((location, index) => {
            const icon = this.getServiceIcon(location.service_type);
            const marker = L.marker([location.latitude, location.longitude], { icon })
                .addTo(targetMap);
            
            const popupContent = this.createPopupContent(location);
            marker.bindPopup(popupContent);
            
            markers.push(marker);
        });
        
        KapitalBankApp.state.markers = markers;
        
        if (locations.length > 1) {
            const group = new L.featureGroup(markers);
            targetMap.fitBounds(group.getBounds().pad(0.1));
        }
        
        return markers;
    },
    
    clearMarkers() {
        KapitalBankApp.state.markers.forEach(marker => {
            if (KapitalBankApp.state.map) {
                KapitalBankApp.state.map.removeLayer(marker);
            }
        });
        KapitalBankApp.state.markers = [];
    },
    
    getServiceIcon(serviceType) {
        const iconConfigs = {
            branch: { icon: '🏛️', color: 'blue' },
            atm: { icon: '🏧', color: 'green' },
            cash_in: { icon: '💰', color: 'orange' },
            digital_center: { icon: '💻', color: 'purple' },
            payment_terminal: { icon: '💳', color: 'red' }
        };
        
        const config = iconConfigs[serviceType] || iconConfigs.branch;
        
        return L.divIcon({
            html: `<div style="background-color: ${config.color}; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; border: 2px solid white; box-shadow: 0 2px 5px rgba(0,0,0,0.3);">
                     <span style="font-size: 14px;">${config.icon}</span>
                   </div>`,
            className: 'custom-div-icon',
            iconSize: [30, 30],
            iconAnchor: [15, 15]
        });
    },
    
    createPopupContent(location) {
        const distance = location.distance_km ? `<br><small class="text-muted">📍 ${Utils.formatDistance(location.distance_km)} away</small>` : '';
        
        return `
            <div class="map-popup">
                <h6 class="mb-1">${location.name}</h6>
                <p class="mb-1 small">${location.address}</p>
                <p class="mb-1 small"><strong>📞</strong> ${location.contact?.phone || '+994 12 409 00 00'}</p>
                ${distance}
                <div class="mt-2">
                    <button class="btn btn-sm btn-primary" onclick="MapManager.getDirections(${location.latitude}, ${location.longitude})">
                        <i class="bi bi-navigation me-1"></i>Directions
                    </button>
                </div>
            </div>
        `;
    },
    
    getDirections(lat, lng) {
        const userLocation = KapitalBankApp.state.currentLocation;
        if (userLocation) {
            const url = `https://www.google.com/maps/dir/${userLocation[0]},${userLocation[1]}/${lat},${lng}`;
            window.open(url, '_blank');
        } else {
            const url = `https://www.google.com/maps/search/${lat},${lng}`;
            window.open(url, '_blank');
        }
    }
};

// Currency Services
const CurrencyService = {
    async getCurrentRates() {
        try {
            const result = await Utils.apiCall('/api/currency/rates');
            return result;
        } catch (error) {
            Utils.showAlert('error', `Failed to get currency rates: ${error.message}`);
            return null;
        }
    },
    
    async compareRates(currency, amount = 1000) {
        try {
            const result = await Utils.apiCall('/api/currency/compare', {
                method: 'POST',
                body: JSON.stringify({ currency, amount })
            });
            return result;
        } catch (error) {
            Utils.showAlert('error', `Failed to compare rates for ${currency}: ${error.message}`);
            return null;
        }
    },
    
    convertCurrency(amount, fromCurrency, toCurrency, rates) {
        if (!rates || !amount) return 0;
        
        if (toCurrency === 'AZN') {
            const rate = rates[fromCurrency];
            return rate ? amount * rate : 0;
        }
        
        if (fromCurrency === 'AZN') {
            const rate = rates[toCurrency];
            return rate ? amount / rate : 0;
        }
        
        const fromRate = rates[fromCurrency];
        const toRate = rates[toCurrency];
        if (fromRate && toRate) {
            const aznAmount = amount * fromRate;
            return aznAmount / toRate;
        }
        
        return 0;
    },
    
    updateCurrencyDisplay(rates) {
        const containers = document.querySelectorAll('[data-currency]');
        containers.forEach(container => {
            const currency = container.dataset.currency;
            const rate = rates[currency];
            if (rate) {
                const rateElement = container.querySelector('.currency-rate');
                if (rateElement) {
                    rateElement.textContent = rate.toFixed(4);
                }
            }
        });
    }
};

// Chat System
const ChatSystem = {
    init() {
        const chatForm = document.getElementById('chatForm');
        const messageInput = document.getElementById('messageInput');
        
        if (chatForm && messageInput) {
            chatForm.addEventListener('submit', this.handleSubmit.bind(this));
            messageInput.addEventListener('keydown', this.handleKeydown.bind(this));
        }
    },
    
    async handleSubmit(event) {
        event.preventDefault();
        
        const messageInput = document.getElementById('messageInput');
        const message = messageInput.value.trim();
        
        if (!message) return;
        
        messageInput.value = '';
        this.addMessage('user', message);
        this.showTypingIndicator();
        
        try {
            const result = await Utils.apiCall('/api/chat', {
                method: 'POST',
                body: JSON.stringify({
                    message,
                    language: KapitalBankApp.state.currentLanguage,
                    user_location: KapitalBankApp.state.currentLocation
                })
            });
            
            this.removeTypingIndicator();
            this.addMessage('assistant', result.response);
            
            if (result.suggestions && result.suggestions.length > 0) {
                this.showSuggestions(result.suggestions);
            }
            
        } catch (error) {
            this.removeTypingIndicator();
            this.addMessage('assistant', 'Sorry, I\'m having trouble processing your request right now. Please try again later.');
            Utils.showAlert('error', `Chat error: ${error.message}`);
        }
    },
    
    handleKeydown(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            document.getElementById('chatForm').dispatchEvent(new Event('submit'));
        }
    },
    
    addMessage(sender, message) {
        const chatContainer = document.getElementById('chatMessages');
        if (!chatContainer) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${sender} fade-in`;
        
        const time = new Date().toLocaleTimeString();
        const senderName = sender === 'user' ? 'You' : 'AI Assistant';
        
        messageDiv.innerHTML = `
            <div class="d-flex justify-content-between align-items-start mb-1">
                <strong>${senderName}</strong>
                <small class="opacity-75">${time}</small>
            </div>
            <div>${this.formatMessage(message)}</div>
        `;
        
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    },
    
    formatMessage(message) {
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        message = message.replace(urlRegex, '<a href="$1" target="_blank" rel="noopener">$1</a>');
        
        const phoneRegex = /(\+994\s?\d{2}\s?\d{3}\s?\d{2}\s?\d{2})/g;
        message = message.replace(phoneRegex, '<a href="tel:$1">$1</a>');
        
        const currencyRegex = /(\d+\.?\d*\s?(AZN|USD|EUR|RUB|TRY|GBP))/g;
        message = message.replace(currencyRegex, '<strong class="text-primary">$1</strong>');
        
        return message;
    },
    
    showTypingIndicator() {
        const chatContainer = document.getElementById('chatMessages');
        if (!chatContainer) return;
        
        const typingDiv = document.createElement('div');
        typingDiv.id = 'typing-indicator';
        typingDiv.className = 'typing-indicator';
        typingDiv.innerHTML = `
            <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
        
        chatContainer.appendChild(typingDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    },
    
    removeTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    },
    
    showSuggestions(suggestions) {
        const suggestionsContainer = document.getElementById('suggestions');
        if (!suggestionsContainer) return;
        
        let html = '<div class="d-flex flex-wrap gap-2 mb-2">';
        html += '<small class="text-muted w-100 mb-1">💡 Suggested questions:</small>';
        
        suggestions.forEach((suggestion, index) => {
            html += `
                <button class="btn btn-outline-primary btn-sm fade-in" 
                        onclick="ChatSystem.sendSuggestion('${suggestion.replace(/'/g, "\\'")}')"
                        style="animation-delay: ${index * 0.1}s">
                    ${suggestion}
                </button>
            `;
        });
        html += '</div>';
        
        suggestionsContainer.innerHTML = html;
        
        setTimeout(() => {
            if (suggestionsContainer.innerHTML === html) {
                suggestionsContainer.innerHTML = '';
            }
        }, 30000);
    },
    
    sendSuggestion(suggestion) {
        document.getElementById('messageInput').value = suggestion;
        document.getElementById('chatForm').dispatchEvent(new Event('submit'));
        
        const suggestionsContainer = document.getElementById('suggestions');
        if (suggestionsContainer) {
            suggestionsContainer.innerHTML = '';
        }
    },
    
    clearChat() {
        const chatContainer = document.getElementById('chatMessages');
        if (chatContainer) {
            chatContainer.innerHTML = '';
        }
        this.addMessage('assistant', 'Chat cleared. How can I help you today?');
    }
};

// Page-specific functionality
const PageHandlers = {
    home() {
        setInterval(async () => {
            const rates = await CurrencyService.getCurrentRates();
            if (rates) {
                CurrencyService.updateCurrencyDisplay(rates.rates);
            }
        }, KapitalBankApp.config.updateInterval);
    },
    
    locations() {
        const mapContainer = document.getElementById('map');
        if (mapContainer) {
            MapManager.initMap('map');
            
            LocationService.getCurrentLocation().then(location => {
                const userIcon = L.divIcon({
                    html: '<div style="background-color: red; border-radius: 50%; width: 20px; height: 20px; border: 3px solid white; box-shadow: 0 2px 5px rgba(0,0,0,0.3);"></div>',
                    className: 'user-location-icon',
                    iconSize: [20, 20],
                    iconAnchor: [10, 10]
                });
                
                L.marker(location, { icon: userIcon })
                    .addTo(KapitalBankApp.state.map)
                    .bindPopup('📍 Your Location');
            });
        }
        
        document.querySelectorAll('[data-service-type]').forEach(button => {
            button.addEventListener('click', async (e) => {
                const serviceType = e.target.dataset.serviceType;
                await this.searchServices(serviceType);
            });
        });
        
        const searchForm = document.getElementById('locationSearchForm');
        if (searchForm) {
            searchForm.addEventListener('submit', this.handleLocationSearch.bind(this));
        }
    },
    
    currency() {
        const converterForm = document.getElementById('currencyConverter');
        if (converterForm) {
            ['amount', 'fromCurrency', 'toCurrency'].forEach(fieldId => {
                const field = document.getElementById(fieldId);
                if (field) {
                    field.addEventListener('change', this.autoConvert.bind(this));
                    if (fieldId === 'amount') {
                        field.addEventListener('input', Utils.debounce(this.autoConvert.bind(this), 300));
                    }
                }
            });
        }
        
        this.refreshCurrencyRates();
        setInterval(() => {
            this.refreshCurrencyRates();
        }, KapitalBankApp.config.updateInterval);
    },
    
    chat() {
        ChatSystem.init();
    },
    
    async searchServices(serviceType) {
        Utils.showLoading(`Searching for ${serviceType} locations...`);
        
        try {
            const result = await LocationService.findNearbyServices(serviceType);
            
            if (result.locations && result.locations.length > 0) {
                MapManager.addMarkers(result.locations);
                this.displayLocationResults(result.locations, serviceType);
                Utils.showAlert('success', `Found ${result.total_found} ${serviceType} locations`);
            } else {
                Utils.showAlert('warning', `No ${serviceType} locations found in your area`);
            }
        } catch (error) {
            Utils.showAlert('error', `Failed to search for ${serviceType}: ${error.message}`);
        } finally {
            Utils.hideLoading();
        }
    },
    
    async handleLocationSearch(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const serviceType = formData.get('serviceType');
        
        await this.searchServices(serviceType);
    },
    
    displayLocationResults(locations, serviceType) {
        const resultsContainer = document.getElementById('searchResults');
        if (!resultsContainer) return;
        
        let html = `<h4>📍 ${serviceType.charAt(0).toUpperCase() + serviceType.slice(1)} Locations</h4>`;
        
        locations.forEach((location, index) => {
            const distance = location.distance_km ? Utils.formatDistance(location.distance_km) : '';
            
            html += `
                <div class="branch-card" data-location-index="${index}">
                    <div class="row">
                        <div class="col-md-8">
                            <h5>${location.name}</h5>
                            <p class="text-muted mb-1">📍 ${location.address}</p>
                            <p class="text-muted mb-1">📞 ${location.contact?.phone || '+994 12 409 00 00'}</p>
                            ${distance ? `<p class="mb-1"><span class="badge bg-secondary">${distance}</span></p>` : ''}
                        </div>
                        <div class="col-md-4 text-end">
                            <button class="btn btn-primary btn-sm mb-1" onclick="MapManager.getDirections(${location.latitude}, ${location.longitude})">
                                <i class="bi bi-navigation me-1"></i>Directions
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });
        
        resultsContainer.innerHTML = html;
    },
    
    async autoConvert() {
        const amount = parseFloat(document.getElementById('amount')?.value) || 0;
        const fromCurrency = document.getElementById('fromCurrency')?.value;
        const toCurrency = document.getElementById('toCurrency')?.value;
        
        if (amount > 0 && fromCurrency && toCurrency) {
            const rates = await CurrencyService.getCurrentRates();
            if (rates && rates.rates) {
                const result = CurrencyService.convertCurrency(amount, fromCurrency, toCurrency, rates.rates);
                const convertedAmountField = document.getElementById('convertedAmount');
                if (convertedAmountField) {
                    convertedAmountField.value = result.toFixed(4);
                }
                
                this.showConversionDetails(amount, fromCurrency, result, toCurrency, rates.rates);
            }
        }
    },
    
    showConversionDetails(amount, fromCurrency, result, toCurrency, rates) {
        const container = document.getElementById('conversionResult');
        if (!container) return;
        
        let rate;
        if (fromCurrency === 'AZN') {
            rate = 1 / rates[toCurrency];
        } else if (toCurrency === 'AZN') {
            rate = rates[fromCurrency];
        } else {
            rate = rates[fromCurrency] / rates[toCurrency];
        }
        
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
    },
    
    async refreshCurrencyRates() {
        try {
            const rates = await CurrencyService.getCurrentRates();
            if (rates) {
                CurrencyService.updateCurrencyDisplay(rates.rates);
                KapitalBankApp.state.lastUpdate = new Date();
            }
        } catch (error) {
            console.error('Failed to refresh currency rates:', error);
        }
    }
};

// Application initialization
document.addEventListener('DOMContentLoaded', function() {
    LocationService.getCurrentLocation().catch(() => {
        KapitalBankApp.state.currentLocation = KapitalBankApp.config.defaultLocation;
    });
    
    const currentPage = document.body.dataset.page;
    if (currentPage && PageHandlers[currentPage]) {
        PageHandlers[currentPage]();
    }
    
    setupGlobalEventListeners();
    setupNetworkMonitoring();
    
    console.log('🏛️ Kapital Bank AI Assistant initialized');
});

// Global event listeners
function setupGlobalEventListeners() {
    window.quickConvert = function(amount, from, to) {
        if (document.getElementById('amount')) {
            document.getElementById('amount').value = amount;
            document.getElementById('fromCurrency').value = from;
            document.getElementById('toCurrency').value = to;
            PageHandlers.autoConvert();
        }
    };
    
    window.swapCurrencies = function() {
        const fromSelect = document.getElementById('fromCurrency');
        const toSelect = document.getElementById('toCurrency');
        
        if (fromSelect && toSelect) {
            const fromValue = fromSelect.value;
            fromSelect.value = toSelect.value;
            toSelect.value = fromValue;
            PageHandlers.autoConvert();
        }
    };
    
    window.clearChat = function() {
        if (confirm('Are you sure you want to clear the chat history?')) {
            ChatSystem.clearChat();
        }
    };
}

// Network status monitoring
function setupNetworkMonitoring() {
    function updateOnlineStatus() {
        KapitalBankApp.state.isOnline = navigator.onLine;
        const indicator = document.getElementById('offlineIndicator');
        
        if (indicator) {
            if (navigator.onLine) {
                indicator.classList.add('d-none');
            } else {
                indicator.classList.remove('d-none');
            }
        }
    }
    
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
    
    updateOnlineStatus();
}

// Global functions for template compatibility
window.setLanguage = function(lang) {
    KapitalBankApp.state.currentLanguage = lang;
    localStorage.setItem('language', lang);
    
    document.getElementById('currentLanguage').textContent = lang.toUpperCase();
    
    document.dispatchEvent(new CustomEvent('languageChanged', { 
        detail: { language: lang } 
    }));
};

window.sendQuickQuestion = function(question) {
    if (document.getElementById('messageInput')) {
        document.getElementById('messageInput').value = question;
        document.getElementById('chatForm').dispatchEvent(new Event('submit'));
    }
};

// Export for external use
window.KapitalBankApp = KapitalBankApp;
window.Utils = Utils;
window.LocationService = LocationService;
window.MapManager = MapManager;
window.CurrencyService = CurrencyService;
window.ChatSystem = ChatSystem;