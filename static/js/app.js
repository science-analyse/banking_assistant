/**
 * Kapital Bank AI Assistant - Enhanced Frontend JavaScript
 * Your existing code + essential mobile and dark mode fixes
 */

// Enhanced global application state
window.KapitalBankApp = {
    config: {
        defaultLocation: [40.4093, 49.8671], // Baku center
        mapZoom: 12,
        mobileMapZoom: 11, // Better zoom for mobile
        searchRadius: 5,
        apiBaseUrl: window.location.origin,
        updateInterval: 300000, // 5 minutes
        debounceDelay: 300,
        mobileBreakpoint: 768
    },
    
    state: {
        currentLocation: null,
        map: null,
        markers: [],
        currentLanguage: localStorage.getItem('language') || 'en',
        isOnline: navigator.onLine,
        lastUpdate: null,
        isMobile: window.innerWidth <= 768, // Track mobile state
        touchDevice: 'ontouchstart' in window, // Track touch capability
        isLoading: false
    },
    
    features: {
        geolocation: 'geolocation' in navigator,
        notifications: 'Notification' in window,
        vibration: 'vibrate' in navigator
    }
};

// Enhanced utility functions with mobile support
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
    
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },
    
    formatDistance(distance) {
        if (distance < 1) {
            return `${Math.round(distance * 1000)}m`;
        }
        return `${distance.toFixed(1)}km`;
    },
    
    formatCurrency(amount, currency = 'AZN', precision = 4) {
        try {
            // Use fewer decimals on mobile for better readability
            const finalPrecision = KapitalBankApp.state.isMobile ? Math.min(precision, 2) : precision;
            
            return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: currency,
                minimumFractionDigits: finalPrecision,
                maximumFractionDigits: finalPrecision
            }).format(amount);
        } catch (error) {
            return `${amount.toFixed(precision)} ${currency}`;
        }
    },
    
    showLoading(message = 'Loading...') {
        KapitalBankApp.state.isLoading = true;
        const modal = new bootstrap.Modal(document.getElementById('loadingModal'));
        const loadingText = document.getElementById('loadingText');
        if (loadingText) {
            loadingText.textContent = message;
        }
        modal.show();
        
        // Auto-hide after 30 seconds to prevent stuck loading
        setTimeout(() => {
            if (KapitalBankApp.state.isLoading) {
                this.hideLoading();
                this.showAlert('warning', 'Operation timed out. Please try again.', 5000);
            }
        }, 30000);
    },
    
    hideLoading() {
        KapitalBankApp.state.isLoading = false;
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
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        
        alertContainer.insertAdjacentHTML('beforeend', alertHTML);
        
        // Announce to screen readers
        this.announceToScreenReader(message);
        
        if (duration > 0) {
            setTimeout(() => {
                const alert = document.getElementById(alertId);
                if (alert) {
                    const bsAlert = bootstrap.Alert.getInstance(alert);
                    if (bsAlert) {
                        bsAlert.close();
                    } else {
                        alert.remove();
                    }
                }
            }, duration);
        }
    },
    
    // New: Screen reader announcements
    announceToScreenReader(message) {
        const announcement = document.createElement('div');
        announcement.setAttribute('aria-live', 'polite');
        announcement.setAttribute('aria-atomic', 'true');
        announcement.className = 'sr-only';
        announcement.textContent = message;
        
        document.body.appendChild(announcement);
        
        setTimeout(() => {
            document.body.removeChild(announcement);
        }, 1000);
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
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
            
            const response = await fetch(`${KapitalBankApp.config.apiBaseUrl}${endpoint}`, {
                signal: controller.signal,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            if (error.name === 'AbortError') {
                throw new Error('Request timed out. Please check your connection and try again.');
            }
            console.error(`API call failed for ${endpoint}:`, error);
            throw error;
        }
    },
    
    // New: Mobile utilities
    vibrate(pattern = [100]) {
        if (KapitalBankApp.features.vibration && KapitalBankApp.state.touchDevice) {
            navigator.vibrate(pattern);
        }
    },
    
    isMobileDevice() {
        return KapitalBankApp.state.isMobile || KapitalBankApp.state.touchDevice;
    },
    
    // Enhanced error handling
    handleError(error, context = 'Operation') {
        console.error(`${context} failed:`, error);
        
        let userMessage = `${context} failed. `;
        
        if (!navigator.onLine) {
            userMessage += 'Please check your internet connection.';
        } else if (error.message.includes('timeout')) {
            userMessage += 'The request timed out. Please try again.';
        } else if (error.message.includes('404')) {
            userMessage += 'Service not found.';
        } else if (error.message.includes('500')) {
            userMessage += 'Server error. Please try again later.';
        } else {
            userMessage += 'Please try again.';
        }
        
        this.showAlert('error', userMessage);
        this.vibrate([50, 100, 50]); // Error vibration pattern
    }
};

// Enhanced location services with mobile optimizations
const LocationService = {
    async getCurrentLocation() {
        return new Promise((resolve, reject) => {
            if (!KapitalBankApp.features.geolocation) {
                console.warn('Geolocation not supported');
                const defaultLocation = KapitalBankApp.config.defaultLocation;
                KapitalBankApp.state.currentLocation = defaultLocation;
                resolve(defaultLocation);
                return;
            }
            
            const options = {
                enableHighAccuracy: !KapitalBankApp.state.isMobile, // Less accurate but faster on mobile
                timeout: KapitalBankApp.state.isMobile ? 15000 : 10000, // Longer timeout on mobile
                maximumAge: 300000 // 5 minutes
            };
            
            navigator.geolocation.getCurrentPosition(
                position => {
                    const location = [position.coords.latitude, position.coords.longitude];
                    KapitalBankApp.state.currentLocation = location;
                    
                    // Store for offline use
                    localStorage.setItem('lastKnownLocation', JSON.stringify({
                        coords: location,
                        timestamp: Date.now()
                    }));
                    
                    resolve(location);
                },
                error => {
                    console.warn('Geolocation error:', error);
                    
                    // Try to use last known location
                    const lastKnown = this.getLastKnownLocation();
                    if (lastKnown) {
                        KapitalBankApp.state.currentLocation = lastKnown;
                        resolve(lastKnown);
                    } else {
                        const defaultLocation = KapitalBankApp.config.defaultLocation;
                        KapitalBankApp.state.currentLocation = defaultLocation;
                        resolve(defaultLocation);
                    }
                },
                options
            );
        });
    },
    
    // New: Get last known location from storage
    getLastKnownLocation() {
        try {
            const stored = localStorage.getItem('lastKnownLocation');
            if (stored) {
                const data = JSON.parse(stored);
                // Use if less than 1 hour old
                if (Date.now() - data.timestamp < 3600000) {
                    return data.coords;
                }
            }
        } catch (error) {
            console.warn('Error retrieving last known location:', error);
        }
        return null;
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
                    limit: KapitalBankApp.state.isMobile ? 10 : 20 // Fewer results on mobile
                })
            });
            
            return result;
        } catch (error) {
            Utils.handleError(error, `Finding ${serviceType} locations`);
            return { locations: [], total_found: 0 };
        }
    }
};

// Enhanced map management with mobile optimizations
const MapManager = {
    initMap(containerId, center = null) {
        const mapCenter = center || KapitalBankApp.state.currentLocation || KapitalBankApp.config.defaultLocation;
        const isMobile = KapitalBankApp.state.isMobile;
        
        // Mobile-optimized map options
        const mapOptions = {
            zoomControl: !isMobile, // Hide zoom control on mobile to save space
            attributionControl: !isMobile,
            scrollWheelZoom: !isMobile,
            doubleClickZoom: true,
            touchZoom: isMobile,
            dragging: true,
            tap: isMobile
        };
        
        const zoom = isMobile ? KapitalBankApp.config.mobileMapZoom : KapitalBankApp.config.mapZoom;
        const map = L.map(containerId, mapOptions).setView(mapCenter, zoom);
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: isMobile ? '' : '© OpenStreetMap contributors',
            maxZoom: 18
        }).addTo(map);
        
        // Add mobile-specific controls
        if (isMobile) {
            this.addMobileControls(map);
        }
        
        // Handle map resize on orientation change
        if (KapitalBankApp.state.touchDevice) {
            window.addEventListener('orientationchange', () => {
                setTimeout(() => {
                    map.invalidateSize();
                }, 500);
            });
        }
        
        KapitalBankApp.state.map = map;
        return map;
    },
    
    // New: Add mobile-specific controls
    addMobileControls(map) {
        // Add locate button for mobile
        const locateControl = L.control({ position: 'topright' });
        locateControl.onAdd = function() {
            const div = L.DomUtil.create('div', 'leaflet-bar leaflet-control leaflet-control-custom');
            div.innerHTML = '<button class="btn btn-light btn-sm" onclick="MapManager.centerOnUser()" title="Center on my location" aria-label="Center map on my location"><i class="bi bi-crosshair"></i></button>';
            div.style.backgroundColor = 'white';
            div.style.padding = '5px';
            div.style.borderRadius = '4px';
            return div;
        };
        locateControl.addTo(map);
    },
    
    // New: Center map on user location
    centerOnUser() {
        LocationService.getCurrentLocation().then(location => {
            if (KapitalBankApp.state.map) {
                const zoom = KapitalBankApp.state.isMobile ? 15 : 16;
                KapitalBankApp.state.map.setView(location, zoom);
                Utils.vibrate([100]); // Success vibration
            }
        }).catch(error => {
            Utils.handleError(error, 'Getting your location');
        });
    },
    
    addMarkers(locations, map = null) {
        const targetMap = map || KapitalBankApp.state.map;
        if (!targetMap) return;
        
        this.clearMarkers();
        
        const markers = [];
        const isMobile = KapitalBankApp.state.isMobile;
        
        locations.forEach((location, index) => {
            const icon = this.getServiceIcon(location.service_type, isMobile);
            const marker = L.marker([location.latitude, location.longitude], { icon })
                .addTo(targetMap);
            
            const popupContent = this.createPopupContent(location, isMobile);
            
            // Mobile-optimized popup options
            const popupOptions = isMobile ? {
                maxWidth: 250,
                closeButton: true,
                autoClose: true,
                keepInView: true
            } : {
                maxWidth: 300
            };
            
            marker.bindPopup(popupContent, popupOptions);
            
            // Add haptic feedback for mobile
            if (isMobile) {
                marker.on('click', () => {
                    Utils.vibrate([50]);
                });
            }
            
            markers.push(marker);
        });
        
        KapitalBankApp.state.markers = markers;
        
        if (locations.length > 1) {
            const group = new L.featureGroup(markers);
            const bounds = group.getBounds();
            // Add padding for mobile
            const padding = isMobile ? [20, 20] : [50, 50];
            targetMap.fitBounds(bounds, { padding });
        } else if (locations.length === 1) {
            // Center on single location with appropriate zoom
            const zoom = isMobile ? 15 : 16;
            targetMap.setView([locations[0].latitude, locations[0].longitude], zoom);
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
    
    getServiceIcon(serviceType, isMobile = false) {
        const iconConfigs = {
            branch: { icon: '🏛️', color: '#1f4e79' },
            atm: { icon: '🏧', color: '#28a745' },
            cash_in: { icon: '💰', color: '#ffc107' },
            digital_center: { icon: '💻', color: '#6f42c1' },
            payment_terminal: { icon: '💳', color: '#dc3545' }
        };
        
        const config = iconConfigs[serviceType] || iconConfigs.branch;
        const size = isMobile ? 25 : 30;
        const fontSize = isMobile ? '12px' : '14px';
        
        return L.divIcon({
            html: `<div style="background-color: ${config.color}; border-radius: 50%; width: ${size}px; height: ${size}px; display: flex; align-items: center; justify-content: center; border: 2px solid white; box-shadow: 0 2px 5px rgba(0,0,0,0.3); font-size: ${fontSize};">
                     <span>${config.icon}</span>
                   </div>`,
            className: 'custom-div-icon',
            iconSize: [size, size],
            iconAnchor: [size/2, size/2]
        });
    },
    
    createPopupContent(location, isMobile = false) {
        const distance = location.distance_km ? `<br><small class="text-muted">📍 ${Utils.formatDistance(location.distance_km)} away</small>` : '';
        
        return `
            <div class="map-popup">
                <h6 class="mb-1">${location.name}</h6>
                <p class="mb-1 small">${location.address}</p>
                <p class="mb-1 small"><strong>📞</strong> ${location.contact?.phone || '+994 12 409 00 00'}</p>
                ${distance}
                <div class="mt-2 ${isMobile ? 'd-grid gap-1' : ''}">
                    <button class="btn btn-sm btn-primary" onclick="MapManager.getDirections(${location.latitude}, ${location.longitude})">
                        <i class="bi bi-navigation me-1"></i>Directions
                    </button>
                    ${isMobile ? `
                        <button class="btn btn-sm btn-outline-secondary" onclick="MapManager.shareLocation(${location.latitude}, ${location.longitude}, '${location.name.replace(/'/g, "\\'")}')">
                            <i class="bi bi-share me-1"></i>Share
                        </button>
                    ` : ''}
                </div>
            </div>
        `;
    },
    
    getDirections(lat, lng) {
        const userLocation = KapitalBankApp.state.currentLocation;
        
        // Enhanced mobile support - try to open native apps
        if (KapitalBankApp.state.touchDevice) {
            const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
            const isAndroid = /Android/.test(navigator.userAgent);
            
            if (isIOS) {
                const url = userLocation 
                    ? `http://maps.apple.com/?saddr=${userLocation[0]},${userLocation[1]}&daddr=${lat},${lng}`
                    : `http://maps.apple.com/?daddr=${lat},${lng}`;
                window.open(url, '_blank');
            } else if (isAndroid) {
                const url = userLocation
                    ? `https://www.google.com/maps/dir/${userLocation[0]},${userLocation[1]}/${lat},${lng}`
                    : `https://www.google.com/maps/search/${lat},${lng}`;
                window.open(url, '_blank');
            } else {
                // Fallback to Google Maps
                const url = userLocation
                    ? `https://www.google.com/maps/dir/${userLocation[0]},${userLocation[1]}/${lat},${lng}`
                    : `https://www.google.com/maps/search/${lat},${lng}`;
                window.open(url, '_blank');
            }
        } else {
            // Desktop behavior
            if (userLocation) {
                const url = `https://www.google.com/maps/dir/${userLocation[0]},${userLocation[1]}/${lat},${lng}`;
                window.open(url, '_blank');
            } else {
                const url = `https://www.google.com/maps/search/${lat},${lng}`;
                window.open(url, '_blank');
            }
        }
        
        Utils.vibrate([100, 50, 100]); // Success pattern
    },
    
    // New: Share location functionality for mobile
    shareLocation(lat, lng, name) {
        if (navigator.share && KapitalBankApp.state.touchDevice) {
            navigator.share({
                title: `${name} - Kapital Bank`,
                text: `Check out this Kapital Bank location: ${name}`,
                url: `https://www.google.com/maps/search/${lat},${lng}`
            }).catch(error => {
                console.warn('Error sharing:', error);
                this.fallbackShare(lat, lng, name);
            });
        } else {
            this.fallbackShare(lat, lng, name);
        }
    },
    
    fallbackShare(lat, lng, name) {
        const url = `https://www.google.com/maps/search/${lat},${lng}`;
        
        if (navigator.clipboard) {
            navigator.clipboard.writeText(url).then(() => {
                Utils.showAlert('success', 'Location link copied to clipboard!', 3000);
            }).catch(() => {
                Utils.showAlert('info', `Share this link: ${url}`, 8000);
            });
        } else {
            Utils.showAlert('info', `Share this link: ${url}`, 8000);
        }
    }
};

// Enhanced currency services
const CurrencyService = {
    cache: new Map(),
    cacheTimeout: 300000, // 5 minutes
    
    async getCurrentRates(useCache = true) {
        const cacheKey = 'current_rates';
        
        if (useCache) {
            const cached = this.cache.get(cacheKey);
            if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
                return cached.data;
            }
        }
        
        try {
            const result = await Utils.apiCall('/api/currency/rates');
            
            if (result) {
                this.cache.set(cacheKey, {
                    data: result,
                    timestamp: Date.now()
                });
            }
            
            return result;
        } catch (error) {
            Utils.handleError(error, 'Getting currency rates');
            
            // Return cached data if available, even if expired
            const cached = this.cache.get(cacheKey);
            return cached ? cached.data : null;
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
            Utils.handleError(error, `Comparing rates for ${currency}`);
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
                    // Use appropriate precision for mobile
                    const precision = KapitalBankApp.state.isMobile ? 3 : 4;
                    rateElement.textContent = rate.toFixed(precision);
                }
            }
        });
    }
};

// Enhanced chat system with mobile improvements
const ChatSystem = {
    messageHistory: [],
    maxHistory: 50,
    isTyping: false,
    
    init() {
        const chatForm = document.getElementById('chatForm');
        const messageInput = document.getElementById('messageInput');
        
        if (chatForm && messageInput) {
            chatForm.addEventListener('submit', this.handleSubmit.bind(this));
            messageInput.addEventListener('keydown', this.handleKeydown.bind(this));
            
            // Mobile-specific improvements
            if (KapitalBankApp.state.touchDevice) {
                this.setupMobileChat(messageInput);
            }
        }
        
        // Load message history
        this.loadMessageHistory();
    },
    
    // New: Mobile chat optimizations
    setupMobileChat(input) {
        // Prevent zoom on focus for iOS
        input.addEventListener('focus', () => {
            if (/iPad|iPhone|iPod/.test(navigator.userAgent)) {
                input.style.fontSize = '16px';
            }
        });
        
        // Add haptic feedback
        input.addEventListener('input', Utils.throttle(() => {
            Utils.vibrate([10]);
        }, 100));
        
        // Auto-resize input
        input.addEventListener('input', () => {
            input.style.height = 'auto';
            input.style.height = Math.min(input.scrollHeight, 120) + 'px';
        });
    },
    
    async handleSubmit(event) {
        event.preventDefault();
        
        const messageInput = document.getElementById('messageInput');
        const message = messageInput.value.trim();
        
        if (!message || this.isTyping) return;
        
        messageInput.value = '';
        messageInput.style.height = 'auto'; // Reset height
        
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
            
            // Save to history
            this.saveMessageToHistory(message, result.response);
            
            if (result.suggestions && result.suggestions.length > 0) {
                this.showSuggestions(result.suggestions);
            }
            
            Utils.vibrate([50, 50, 50]); // Success pattern
            
        } catch (error) {
            this.removeTypingIndicator();
            const errorMessage = KapitalBankApp.state.currentLanguage === 'az' 
                ? 'Üzr istəyirəm, hal-hazırda texniki problemlər var. Xahiş edirəm yenidən cəhd edin.'
                : 'Sorry, I\'m having trouble processing your request right now. Please try again later.';
                
            this.addMessage('assistant', errorMessage);
            Utils.handleError(error, 'Chat');
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
        
        const time = new Date().toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
        const senderName = sender === 'user' 
            ? (KapitalBankApp.state.currentLanguage === 'az' ? 'Siz' : 'You')
            : (KapitalBankApp.state.currentLanguage === 'az' ? 'AI Köməkçi' : 'AI Assistant');
        
        messageDiv.innerHTML = `
            <div class="d-flex justify-content-between align-items-start mb-1">
                <strong>${senderName}</strong>
                <small class="opacity-75">${time}</small>
            </div>
            <div>${this.formatMessage(message)}</div>
        `;
        
        chatContainer.appendChild(messageDiv);
        
        // Smooth scroll to bottom
        if ('scrollBehavior' in document.documentElement.style) {
            chatContainer.scrollTo({
                top: chatContainer.scrollHeight,
                behavior: 'smooth'
            });
        } else {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
        
        // Announce to screen readers
        Utils.announceToScreenReader(`${senderName}: ${message}`);
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
        
        this.isTyping = true;
        
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
        this.isTyping = false;
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    },
    
    showSuggestions(suggestions) {
        const suggestionsContainer = document.getElementById('suggestions');
        if (!suggestionsContainer) return;
        
        const isMobile = KapitalBankApp.state.isMobile;
        
        let html = '<div class="d-flex flex-wrap gap-2 mb-2">';
        html += `<small class="text-muted w-100 mb-1">${KapitalBankApp.state.currentLanguage === 'az' ? '💡 Təklif olunan suallar:' : '💡 Suggested questions:'}</small>`;
        
        // Show fewer suggestions on mobile
        suggestions.slice(0, isMobile ? 3 : 4).forEach((suggestion, index) => {
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
        const messageInput = document.getElementById('messageInput');
        if (messageInput) {
            messageInput.value = suggestion;
            messageInput.focus();
            
            // Auto-send after a brief delay for better UX on mobile
            if (KapitalBankApp.state.touchDevice) {
                setTimeout(() => {
                    document.getElementById('chatForm').dispatchEvent(new Event('submit'));
                }, 500);
            } else {
                document.getElementById('chatForm').dispatchEvent(new Event('submit'));
            }
        }
        
        const suggestionsContainer = document.getElementById('suggestions');
        if (suggestionsContainer) {
            suggestionsContainer.innerHTML = '';
        }
        
        Utils.vibrate([50]);
    },
    
    clearChat() {
        const chatContainer = document.getElementById('chatMessages');
        if (chatContainer) {
            chatContainer.innerHTML = '';
        }
        
        // Clear history
        this.messageHistory = [];
        localStorage.removeItem('chatHistory');
        
        const welcomeMessage = KapitalBankApp.state.currentLanguage === 'az' 
            ? 'Söhbət təmizləndi. Bu gün sizə necə kömək edə bilərəm?'
            : 'Chat cleared. How can I help you today?';
            
        this.addMessage('assistant', welcomeMessage);
    },
    
    // New: Save message history
    saveMessageToHistory(userMessage, assistantMessage) {
        const entry = {
            user: userMessage,
            assistant: assistantMessage,
            timestamp: Date.now()
        };
        
        this.messageHistory.push(entry);
        
        // Keep only last 50 messages
        if (this.messageHistory.length > this.maxHistory) {
            this.messageHistory = this.messageHistory.slice(-this.maxHistory);
        }
        
        // Save to localStorage
        try {
            localStorage.setItem('chatHistory', JSON.stringify(this.messageHistory));
        } catch (error) {
            console.warn('Could not save chat history:', error);
        }
    },
    
    // New: Load message history
    loadMessageHistory() {
        try {
            const saved = localStorage.getItem('chatHistory');
            if (saved) {
                this.messageHistory = JSON.parse(saved);
                
                // Remove old messages (older than 7 days)
                const weekAgo = Date.now() - (7 * 24 * 60 * 60 * 1000);
                this.messageHistory = this.messageHistory.filter(entry => entry.timestamp > weekAgo);
                
                // Update localStorage
                localStorage.setItem('chatHistory', JSON.stringify(this.messageHistory));
            }
        } catch (error) {
            console.warn('Could not load chat history:', error);
            this.messageHistory = [];
        }
    }
};

// Enhanced page-specific functionality with mobile support
const PageHandlers = {
    home() {
        // Periodic currency rate updates
        setInterval(async () => {
            try {
                const rates = await CurrencyService.getCurrentRates();
                if (rates) {
                    CurrencyService.updateCurrencyDisplay(rates.rates);
                }
            } catch (error) {
                console.warn('Periodic rate update failed:', error);
            }
        }, KapitalBankApp.config.updateInterval);
        
        // Setup intersection observer for animations if available
        if ('IntersectionObserver' in window) {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('fade-in');
                    }
                });
            }, { threshold: 0.1 });
            
            document.querySelectorAll('.service-card, .feature-card').forEach(card => {
                observer.observe(card);
            });
        }
    },
    
    locations() {
        const mapContainer = document.getElementById('map');
        if (mapContainer) {
            MapManager.initMap('map');
            
            LocationService.getCurrentLocation().then(location => {
                // Add user location marker with mobile-optimized styling
                const userIcon = L.divIcon({
                    html: '<div style="background-color: #dc3545; border-radius: 50%; width: 20px; height: 20px; border: 3px solid white; box-shadow: 0 2px 5px rgba(0,0,0,0.3); animation: pulse 2s infinite;"></div>',
                    className: 'user-location-icon',
                    iconSize: [20, 20],
                    iconAnchor: [10, 10]
                });
                
                L.marker(location, { icon: userIcon })
                    .addTo(KapitalBankApp.state.map)
                    .bindPopup(KapitalBankApp.state.currentLanguage === 'az' ? '📍 Sizin Məkanınız' : '📍 Your Location');
            }).catch(error => {
                console.warn('Could not get user location:', error);
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
        
        // Auto-search if service type is specified in session storage (from home page)
        const searchServiceType = sessionStorage.getItem('searchServiceType');
        if (searchServiceType) {
            document.getElementById('serviceType').value = searchServiceType;
            sessionStorage.removeItem('searchServiceType');
            setTimeout(() => {
                this.searchServices(searchServiceType);
            }, 1000);
        }
        
        // Mobile-specific: Add pull-to-refresh for location updates
        if (KapitalBankApp.state.touchDevice) {
            this.setupMobileLocationFeatures();
        }
    },
    
    // New: Mobile location features
    setupMobileLocationFeatures() {
        let startY = 0;
        let isRefreshing = false;
        
        document.addEventListener('touchstart', (e) => {
            startY = e.touches[0].clientY;
        });
        
        document.addEventListener('touchmove', (e) => {
            const currentY = e.touches[0].clientY;
            const diff = currentY - startY;
            
            if (diff > 100 && window.scrollY === 0 && !isRefreshing) {
                isRefreshing = true;
                Utils.showAlert('info', 'Refreshing location data...', 2000);
                Utils.vibrate([100]);
                
                // Refresh current search
                const activeButton = document.querySelector('[data-service-type].btn-primary');
                if (activeButton) {
                    this.searchServices(activeButton.dataset.serviceType);
                }
                
                setTimeout(() => {
                    isRefreshing = false;
                }, 2000);
            }
        });
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
        
        // Mobile-specific: Add haptic feedback for currency selection
        if (KapitalBankApp.state.touchDevice) {
            document.querySelectorAll('#fromCurrency, #toCurrency').forEach(select => {
                select.addEventListener('change', () => {
                    Utils.vibrate([25]);
                });
            });
        }
        
        this.refreshCurrencyRates();
        setInterval(() => {
            this.refreshCurrencyRates();
        }, KapitalBankApp.config.updateInterval);
    },
    
    chat() {
        ChatSystem.init();
        
        // Check for quick question from home page
        const quickQuestion = sessionStorage.getItem('quickQuestion');
        if (quickQuestion) {
            document.getElementById('messageInput').value = quickQuestion;
            sessionStorage.removeItem('quickQuestion');
            // Auto-send after a brief delay
            setTimeout(() => {
                document.getElementById('chatForm').dispatchEvent(new Event('submit'));
            }, 1000);
        }
    },
    
    async searchServices(serviceType) {
        Utils.showLoading(`Searching for ${serviceType} locations...`);
        
        try {
            // Get current location first
            let location;
            try {
                location = await LocationService.getCurrentLocation();
            } catch (error) {
                location = KapitalBankApp.config.defaultLocation;
                Utils.showAlert('warning', 'Using default location (Baku)', 3000);
            }
            
            const result = await LocationService.findNearbyServices(serviceType, location);
            
            if (result.locations && result.locations.length > 0) {
                MapManager.addMarkers(result.locations);
                this.displayLocationResults(result.locations, serviceType);
                
                const message = KapitalBankApp.state.currentLanguage === 'az'
                    ? `${result.total_found} ${serviceType} məkan tapıldı`
                    : `Found ${result.total_found} ${serviceType} locations`;
                Utils.showAlert('success', message, 3000);
                
                Utils.vibrate([100, 50, 100]); // Success pattern
            } else {
                const message = KapitalBankApp.state.currentLanguage === 'az'
                    ? `Ətrafınızda ${serviceType} məkanı tapılmadı`
                    : `No ${serviceType} locations found in your area`;
                Utils.showAlert('warning', message, 5000);
            }
            
            // Update active button styling
            document.querySelectorAll('[data-service-type]').forEach(btn => {
                btn.classList.remove('btn-primary');
                btn.classList.add('btn-outline-primary');
            });
            const activeBtn = document.querySelector(`[data-service-type="${serviceType}"]`);
            if (activeBtn) {
                activeBtn.classList.remove('btn-outline-primary');
                activeBtn.classList.add('btn-primary');
            }
            
        } catch (error) {
            Utils.handleError(error, `Searching for ${serviceType}`);
        } finally {
            Utils.hideLoading();
        }
    },
    
    async handleLocationSearch(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const serviceType = formData.get('serviceType');
        const searchRadius = parseInt(formData.get('searchRadius')) || 5;
        
        // Update config
        KapitalBankApp.config.searchRadius = searchRadius;
        
        await this.searchServices(serviceType);
    },
    
    displayLocationResults(locations, serviceType) {
        const resultsContainer = document.getElementById('searchResults');
        if (!resultsContainer) return;
        
        const isMobile = KapitalBankApp.state.isMobile;
        const title = KapitalBankApp.state.currentLanguage === 'az'
            ? `📍 ${serviceType} Məkanları`
            : `📍 ${serviceType.charAt(0).toUpperCase() + serviceType.slice(1)} Locations`;
        
        let html = `<h4>${title}</h4>`;
        
        locations.forEach((location, index) => {
            const distance = location.distance_km ? Utils.formatDistance(location.distance_km) : '';
            
            html += `
                <div class="branch-card fade-in" data-location-index="${index}" style="animation-delay: ${index * 0.1}s">
                    <div class="row ${isMobile ? 'text-center' : ''}">
                        <div class="${isMobile ? 'col-12' : 'col-md-8'}">
                            <h5>${location.name}</h5>
                            <p class="text-muted mb-1">📍 ${location.address}</p>
                            <p class="text-muted mb-1">
                                📞 <a href="tel:${location.contact?.phone || '+994124090000'}" class="text-decoration-none">
                                    ${location.contact?.phone || '+994 12 409 00 00'}
                                </a>
                            </p>
                            ${distance ? `<p class="mb-1"><span class="badge bg-secondary">${distance}</span></p>` : ''}
                        </div>
                        <div class="${isMobile ? 'col-12 mt-2' : 'col-md-4 text-end'}">
                            <div class="${isMobile ? 'd-grid gap-1' : ''}">
                                <button class="btn btn-primary btn-sm ${isMobile ? '' : 'mb-1'}" onclick="MapManager.getDirections(${location.latitude}, ${location.longitude})">
                                    <i class="bi bi-navigation me-1"></i>
                                    ${KapitalBankApp.state.currentLanguage === 'az' ? 'İstiqamət' : 'Directions'}
                                </button>
                                ${isMobile ? `
                                    <button class="btn btn-outline-secondary btn-sm" onclick="MapManager.shareLocation(${location.latitude}, ${location.longitude}, '${location.name.replace(/'/g, "\\'")}')">
                                        <i class="bi bi-share me-1"></i>
                                        ${KapitalBankApp.state.currentLanguage === 'az' ? 'Paylaş' : 'Share'}
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        resultsContainer.innerHTML = html;
        
        // Smooth scroll to results on mobile
        if (isMobile) {
            setTimeout(() => {
                resultsContainer.scrollIntoView({ 
                    behavior: 'smooth', 
                    block: 'start' 
                });
            }, 300);
        }
    },
    
    async autoConvert() {
        const amount = parseFloat(document.getElementById('amount')?.value) || 0;
        const fromCurrency = document.getElementById('fromCurrency')?.value;
        const toCurrency = document.getElementById('toCurrency')?.value;
        
        if (amount > 0 && fromCurrency && toCurrency && fromCurrency !== toCurrency) {
            try {
                const rates = await CurrencyService.getCurrentRates();
                if (rates && rates.rates) {
                    const result = CurrencyService.convertCurrency(amount, fromCurrency, toCurrency, rates.rates);
                    const convertedAmountField = document.getElementById('convertedAmount');
                    if (convertedAmountField) {
                        const precision = KapitalBankApp.state.isMobile ? 3 : 4;
                        convertedAmountField.value = result.toFixed(precision);
                    }
                    
                    this.showConversionDetails(amount, fromCurrency, result, toCurrency, rates.rates);
                }
            } catch (error) {
                console.error('Auto-conversion failed:', error);
            }
        }
    },
    
    showConversionDetails(amount, fromCurrency, result, toCurrency, rates) {
        const container = document.getElementById('conversionResult');
        if (!container) return;
        
        let rate;
        if (fromCurrency === 'AZN') {
            rate = rates[toCurrency] ? 1 / rates[toCurrency] : 0;
        } else if (toCurrency === 'AZN') {
            rate = rates[fromCurrency] || 0;
        } else {
            rate = (rates[fromCurrency] && rates[toCurrency]) 
                ? rates[fromCurrency] / rates[toCurrency] 
                : 0;
        }
        
        const precision = KapitalBankApp.state.isMobile ? 4 : 6;
        const resultPrecision = KapitalBankApp.state.isMobile ? 3 : 4;
        
        container.innerHTML = `
            <div class="alert alert-info">
                <div class="d-flex justify-content-between align-items-center ${KapitalBankApp.state.isMobile ? 'flex-column text-center' : ''}">
                    <div ${KapitalBankApp.state.isMobile ? 'class="mb-2"' : ''}>
                        <strong>${amount} ${fromCurrency} = ${result.toFixed(resultPrecision)} ${toCurrency}</strong>
                    </div>
                    <small class="text-muted">Rate: ${rate.toFixed(precision)}</small>
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
            const rates = await CurrencyService.getCurrentRates(false); // Force refresh
            if (rates) {
                CurrencyService.updateCurrencyDisplay(rates.rates);
                KapitalBankApp.state.lastUpdate = new Date();
                
                // Update last update time display
                const updateElements = document.querySelectorAll('#lastUpdateTime, #update-time');
                updateElements.forEach(el => {
                    if (el) {
                        el.textContent = new Date().toLocaleString();
                    }
                });
            }
        } catch (error) {
            console.error('Failed to refresh currency rates:', error);
        }
    }
};

// Enhanced responsive design management
const ResponsiveManager = {
    init() {
        this.updateDeviceInfo();
        this.setupResizeListener();
        this.setupOrientationChangeListener();
    },
    
    updateDeviceInfo() {
        const width = window.innerWidth;
        KapitalBankApp.state.isMobile = width <= KapitalBankApp.config.mobileBreakpoint;
        
        // Update body classes for CSS targeting
        document.body.classList.toggle('mobile', KapitalBankApp.state.isMobile);
        document.body.classList.toggle('desktop', !KapitalBankApp.state.isMobile);
    },
    
    setupResizeListener() {
        const resizeHandler = Utils.throttle(() => {
            this.updateDeviceInfo();
            
            // Invalidate map size if it exists
            if (KapitalBankApp.state.map) {
                setTimeout(() => {
                    KapitalBankApp.state.map.invalidateSize();
                }, 100);
            }
        }, 250);
        
        window.addEventListener('resize', resizeHandler);
    },
    
    setupOrientationChangeListener() {
        if (KapitalBankApp.state.touchDevice) {
            window.addEventListener('orientationchange', () => {
                setTimeout(() => {
                    this.updateDeviceInfo();
                    
                    // Invalidate map
                    if (KapitalBankApp.state.map) {
                        KapitalBankApp.state.map.invalidateSize();
                    }
                }, 500);
            });
        }
    }
};

// Application initialization with enhanced mobile support
document.addEventListener('DOMContentLoaded', function() {
    console.log('🏛️ Initializing Kapital Bank AI Assistant...');
    
    // Initialize responsive manager
    ResponsiveManager.init();
    
    // Get user location
    LocationService.getCurrentLocation().catch(() => {
        KapitalBankApp.state.currentLocation = KapitalBankApp.config.defaultLocation;
        console.log('Using default location (Baku)');
    });
    
    // Initialize page-specific handlers
    const currentPage = document.body.dataset.page;
    if (currentPage && PageHandlers[currentPage]) {
        try {
            PageHandlers[currentPage]();
            console.log(`✅ ${currentPage} page initialized`);
        } catch (error) {
            console.error(`❌ Error initializing ${currentPage} page:`, error);
        }
    }
    
    // Setup global event listeners
    setupGlobalEventListeners();
    
    // Setup network monitoring
    setupNetworkMonitoring();
    
    // Setup accessibility features
    setupAccessibilityFeatures();
    
    console.log('🎉 Kapital Bank AI Assistant ready!');
});

// Enhanced global event listeners
function setupGlobalEventListeners() {
    // Currency converter quick actions with mobile optimization
    window.quickConvert = function(amount, from, to) {
        const amountField = document.getElementById('amount');
        const fromField = document.getElementById('fromCurrency');
        const toField = document.getElementById('toCurrency');
        
        if (amountField && fromField && toField) {
            amountField.value = amount;
            fromField.value = from;
            toField.value = to;
            
            PageHandlers.autoConvert();
            Utils.vibrate([50]); // Haptic feedback
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
            Utils.vibrate([50, 25, 50]); // Swap feedback
        }
    };
    
    window.clearChat = function() {
        const message = KapitalBankApp.state.currentLanguage === 'az'
            ? 'Söhbət tarixçəsini silmək istədiyinizə əminsiniz?'
            : 'Are you sure you want to clear the chat history?';
            
        if (confirm(message)) {
            ChatSystem.clearChat();
            Utils.vibrate([100]);
        }
    };
    
    window.sendQuickQuestion = function(question) {
        if (KapitalBankApp.state.touchDevice) {
            // For mobile, store in session and navigate
            sessionStorage.setItem('quickQuestion', question);
            window.location.href = '/chat';
        } else {
            // For desktop, fill input if on chat page
            const messageInput = document.getElementById('messageInput');
            if (messageInput) {
                messageInput.value = question;
                messageInput.focus();
                document.getElementById('chatForm')?.dispatchEvent(new Event('submit'));
            } else {
                // Navigate to chat page
                sessionStorage.setItem('quickQuestion', question);
                window.location.href = '/chat';
            }
        }
    };
}

// Enhanced network status monitoring
function setupNetworkMonitoring() {
    function updateOnlineStatus() {
        KapitalBankApp.state.isOnline = navigator.onLine;
        const indicator = document.getElementById('connectionStatus') || document.getElementById('offlineIndicator');
        
        if (indicator) {
            if (navigator.onLine) {
                indicator.classList.add('d-none');
                indicator.classList.remove('show');
            } else {
                indicator.classList.remove('d-none');
                indicator.classList.add('show');
            }
        }
        
        // Show user-friendly notification
        if (!navigator.onLine) {
            Utils.showAlert('warning', 'You are offline. Some features may not work properly.', 0);
        } else if (KapitalBankApp.state.isOnline === false) {
            // Just came back online
            Utils.showAlert('success', 'Connection restored!', 3000);
            // Hide any persistent offline alerts
            document.querySelectorAll('.alert-warning').forEach(alert => {
                if (alert.textContent.includes('offline') || alert.textContent.includes('connection')) {
                    const bsAlert = bootstrap.Alert.getInstance(alert);
                    if (bsAlert) bsAlert.close();
                }
            });
        }
    }
    
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
    
    // Initial check
    updateOnlineStatus();
}

// Enhanced accessibility features
function setupAccessibilityFeatures() {
    // Keyboard navigation enhancement
    document.addEventListener('keydown', (e) => {
        // Global shortcuts with Alt key
        if (e.altKey) {
            switch(e.key.toLowerCase()) {
                case 'h':
                    e.preventDefault();
                    window.location.href = '/';
                    break;
                case 'l':
                    e.preventDefault();
                    window.location.href = '/locations';
                    break;
                case 'c':
                    e.preventDefault();
                    window.location.href = '/currency';
                    break;
                case 'a':
                    e.preventDefault();
                    window.location.href = '/chat';
                    break;
            }
        }
        
        // Escape key actions
        if (e.key === 'Escape') {
            // Close any open modals
            const openModal = document.querySelector('.modal.show');
            if (openModal) {
                const modal = bootstrap.Modal.getInstance(openModal);
                if (modal) modal.hide();
            }
            
            // Clear input focus
            if (document.activeElement?.tagName === 'INPUT') {
                document.activeElement.blur();
            }
        }
    });
    
    // Enhanced focus management
    document.addEventListener('focusin', (e) => {
        e.target.classList.add('focused');
    });
    
    document.addEventListener('focusout', (e) => {
        e.target.classList.remove('focused');
    });
}

// Language management
window.setLanguage = function(lang) {
    KapitalBankApp.state.currentLanguage = lang;
    localStorage.setItem('language', lang);
    
    const currentLangEl = document.getElementById('currentLanguage');
    if (currentLangEl) {
        currentLangEl.textContent = lang.toUpperCase();
    }
    
    // Update dropdown active state
    document.querySelectorAll('.dropdown-item[data-lang]').forEach(item => {
        if (item.dataset && item.dataset.lang === lang) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
    
    // Dispatch language change event
    document.dispatchEvent(new CustomEvent('languageChanged', { 
        detail: { language: lang } 
    }));
    
    Utils.vibrate([25]); // Subtle feedback
};

// // Load saved language
// const savedLanguage = localStorage.getItem('language') || 'en';
// if (savedLanguage !== 'en') {
//     setLanguage(savedLanguage);
// }

// Service finder helper for home page
window.findService = function(serviceType) {
    sessionStorage.setItem('searchServiceType', serviceType);
    window.location.href = '/locations';
};

// Export for external use - keeping your original structure
window.KapitalBankApp = KapitalBankApp;
window.Utils = Utils;
window.LocationService = LocationService;
window.MapManager = MapManager;
window.CurrencyService = CurrencyService;
window.ChatSystem = ChatSystem;
window.PageHandlers = PageHandlers;