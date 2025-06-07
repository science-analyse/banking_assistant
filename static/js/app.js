getDirections(lat, lng) {
        const userLocation = KapitalBankApp.state.currentLocation;
        
        // For mobile devices, try to open native maps app
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
            // Desktop - always use Google Maps
            const url = userLocation
                ? `https://www.google.com/maps/dir/${userLocation[0]},${userLocation[1]}/${lat},${lng}`
                : `https://www.google.com/maps/search/${lat},${lng}`;
            window.open(url, '_blank');
        }
        
        Utils.vibrate([100, 50, 100]); // Success pattern
    },
    
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
                this.textAreaFallback(url);
            });
        } else {
            this.textAreaFallback(url);
        }
    },
    
    textAreaFallback(text) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        try {
            document.execCommand('copy');
            Utils.showAlert('success', 'Location link copied!', 3000);
        } catch (err) {
            Utils.showAlert('info', `Share this link: ${text}`, 8000);
        }
        
        document.body.removeChild(textArea);
    }
};

// Enhanced currency service with mobile optimizations
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
        if (!rates || !amount || amount <= 0) return 0;
        
        try {
            if (toCurrency === 'AZN') {
                const rate = rates[fromCurrency];
                return rate ? amount * rate : 0;
            }
            
            if (fromCurrency === 'AZN') {
                const rate = rates[toCurrency];
                return rate ? amount / rate : 0;
            }
            
            // Cross-currency conversion via AZN
            const fromRate = rates[fromCurrency];
            const toRate = rates[toCurrency];
            if (fromRate && toRate) {
                const aznAmount = amount * fromRate;
                return aznAmount / toRate;
            }
            
            return 0;
        } catch (error) {
            console.error('Currency conversion error:', error);
            return 0;
        }
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
    },
    
    // Mobile-specific currency formatting
    formatForMobile(rate, currency) {
        const precision = KapitalBankApp.state.isMobile ? 3 : 4;
        return `${rate.toFixed(precision)} AZN`;
    }
};

// Enhanced chat system with mobile support
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
            
            // Auto-resize input
            this.setupAutoResize(messageInput);
        }
        
        // Load message history
        this.loadMessageHistory();
    },
    
    setupMobileChat(input) {
        // Prevent zoom on focus for iOS
        input.addEventListener('focus', () => {
            if (/iPad|iPhone|iPod/.test(navigator.userAgent)) {
                input.style.fontSize = '16px';
            }
        });
        
        // Add voice input if available
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            this.addVoiceInput(input);
        }
        
        // Add haptic feedback
        input.addEventListener('input', Utils.throttle(() => {
            Utils.vibrate([10]);
        }, 100));
    },
    
    addVoiceInput(input) {
        const voiceButton = document.createElement('button');
        voiceButton.type = 'button';
        voiceButton.className = 'btn btn-outline-secondary';
        voiceButton.innerHTML = '<i class="bi bi-mic"></i>';
        voiceButton.title = 'Voice input';
        voiceButton.setAttribute('aria-label', 'Voice input');
        
        // Insert next to input
        const inputParent = input.parentElement;
        if (inputParent) {
            inputParent.appendChild(voiceButton);
            inputParent.classList.add('d-flex', 'gap-2');
        }
        
        voiceButton.addEventListener('click', () => {
            this.startVoiceRecognition(input);
        });
    },
    
    startVoiceRecognition(input) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        
        recognition.lang = KapitalBankApp.state.currentLanguage === 'az' ? 'az-AZ' : 'en-US';
        recognition.continuous = false;
        recognition.interimResults = false;
        
        recognition.onstart = () => {
            Utils.showAlert('info', 'Listening... Speak now', 3000);
            Utils.vibrate([100]);
        };
        
        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            input.value = transcript;
            input.focus();
            Utils.vibrate([50, 50]);
        };
        
        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            Utils.showAlert('warning', 'Voice input failed. Please try again.', 3000);
        };
        
        recognition.start();
    },
    
    setupAutoResize(input) {
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
        messageInput.style.height = 'auto';
        
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
        messageDiv.setAttribute('role', 'article');
        messageDiv.setAttribute('aria-label', `${sender} message`);
        
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
        this.scrollToBottom(chatContainer);
        
        // Announce to screen readers
        Utils.announceToScreenReader(`${senderName}: ${message}`);
    },
    
    scrollToBottom(container) {
        // Use smooth scrolling if supported
        if ('scrollBehavior' in document.documentElement.style) {
            container.scrollTo({
                top: container.scrollHeight,
                behavior: 'smooth'
            });
        } else {
            // Fallback for older browsers
            container.scrollTop = container.scrollHeight;
        }
    },
    
    formatMessage(message) {
        // URL detection and linking
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        message = message.replace(urlRegex, '<a href="$1" target="_blank" rel="noopener">$1</a>');
        
        // Phone number detection
        const phoneRegex = /(\+994\s?\d{2}\s?\d{3}\s?\d{2}\s?\d{2})/g;
        message = message.replace(phoneRegex, '<a href="tel:$1">$1</a>');
        
        // Currency highlighting
        const currencyRegex = /(\d+\.?\d*\s?(AZN|USD|EUR|RUB|TRY|GBP))/g;
        message = message.replace(currencyRegex, '<strong class="text-primary">$1</strong>');
        
        // Email detection
        const emailRegex = /([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/g;
        message = message.replace(emailRegex, '<a href="mailto:$1">$1</a>');
        
        return message;
    },
    
    showTypingIndicator() {
        const chatContainer = document.getElementById('chatMessages');
        if (!chatContainer) return;
        
        this.isTyping = true;
        
        const typingDiv = document.createElement('div');
        typingDiv.id = 'typing-indicator';
        typingDiv.className = 'typing-indicator';
        typingDiv.setAttribute('aria-label', 'AI is typing');
        typingDiv.innerHTML = `
            <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
        
        chatContainer.appendChild(typingDiv);
        this.scrollToBottom(chatContainer);
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
        
        suggestions.slice(0, isMobile ? 3 : 4).forEach((suggestion, index) => {
            html += `
                <button class="btn btn-outline-primary btn-sm fade-in" 
                        onclick="ChatSystem.sendSuggestion('${suggestion.replace(/'/g, "\\'")}')"
                        style="animation-delay: ${index * 0.1}s"
                        aria-label="Send suggestion: ${suggestion}">
                    ${suggestion}
                </button>
            `;
        });
        html += '</div>';
        
        suggestionsContainer.innerHTML = html;
        
        // Auto-hide suggestions after 30 seconds
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
            
            // Auto-send after a brief delay for better UX
            setTimeout(() => {
                document.getElementById('chatForm').dispatchEvent(new Event('submit'));
            }, 500);
        }
        
        // Clear suggestions
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

// Page-specific handlers with mobile optimizations
const PageHandlers = {
    home() {
        // Lazy load currency rates
        Utils.requestIdleCallback(async () => {
            try {
                const rates = await CurrencyService.getCurrentRates();
                if (rates) {
                    CurrencyService.updateCurrencyDisplay(rates.rates);
                }
            } catch (error) {
                console.warn('Could not load currency rates on home page:', error);
            }
        });
        
        // Set up periodic updates
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
        
        // Setup intersection observer for animations
        this.setupScrollAnimations();
    },
    
    setupScrollAnimations() {
        const observer = Utils.createIntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in');
                }
            });
        });
        
        if (observer) {
            document.querySelectorAll('.service-card, .feature-card').forEach(card => {
                observer.observe(card);
            });
        }
    },
    
    locations() {
        const mapContainer = document.getElementById('map');
        if (mapContainer) {
            // Initialize map with mobile-optimized settings
            MapManager.initMap('map');
            
            // Add user location marker
            LocationService.getCurrentLocation().then(location => {
                this.addUserLocationMarker(location);
            }).catch(error => {
                console.warn('Could not get user location:', error);
            });
        }
        
        // Setup service type buttons
        document.querySelectorAll('[data-service-type]').forEach(button => {
            button.addEventListener('click', async (e) => {
                const serviceType = e.target.dataset.serviceType;
                await this.searchServices(serviceType);
            });
        });
        
        // Setup search form
        const searchForm = document.getElementById('locationSearchForm');
        if (searchForm) {
            searchForm.addEventListener('submit', this.handleLocationSearch.bind(this));
        }
        
        // Auto-search if service type is specified
        const urlParams = new URLSearchParams(window.location.search);
        const serviceType = urlParams.get('service');
        if (serviceType) {
            setTimeout(() => {
                this.searchServices(serviceType);
            }, 1000);
        }
        
        // Setup mobile-specific features
        if (KapitalBankApp.state.touchDevice) {
            this.setupMobileLocationFeatures();
        }
    },
    
    addUserLocationMarker(location) {
        if (!KapitalBankApp.state.map) return;
        
        const userIcon = L.divIcon({
            html: '<div style="background-color: #dc3545; border-radius: 50%; width: 20px; height: 20px; border: 3px solid white; box-shadow: 0 2px 5px rgba(0,0,0,0.3); animation: pulse 2s infinite;"></div>',
            className: 'user-location-icon',
            iconSize: [20, 20],
            iconAnchor: [10, 10]
        });
        
        const marker = L.marker(location, { icon: userIcon })
            .addTo(KapitalBankApp.state.map);
            
        const popupContent = KapitalBankApp.state.currentLanguage === 'az' 
            ? '📍 Sizin Məkanınız' 
            : '📍 Your Location';
            
        marker.bindPopup(popupContent);
        
        // Store reference for cleanup
        KapitalBankApp.state.userMarker = marker;
    },
    
    setupMobileLocationFeatures() {
        // Add pull-to-refresh for mobile
        if ('serviceWorker' in navigator) {
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
                    const activeButton = document.querySelector('[data-service-type].active');
                    if (activeButton) {
                        this.searchServices(activeButton.dataset.serviceType);
                    }
                    
                    setTimeout(() => {
                        isRefreshing = false;
                    }, 2000);
                }
            });
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
            
            // Update active button
            document.querySelectorAll('[data-service-type]').forEach(btn => {
                btn.classList.remove('active');
            });
            document.querySelector(`[data-service-type="${serviceType}"]`)?.classList.add('active');
            
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
            const buttonClass = isMobile ? 'btn-sm' : '';
            
            html += `
                <div class="branch-card fade-in" data-location-index="${index}" style="animation-delay: ${index * 0.1}s">
                    <div class="row align-items-center">
                        <div class="${isMobile ? 'col-12' : 'col-md-8'}">
                            <h5 class="mb-1">${location.name}</h5>
                            <p class="text-muted mb-1">📍 ${location.address}</p>
                            <p class="text-muted mb-1">
                                📞 <a href="tel:${location.contact?.phone || '+994124090000'}" class="text-decoration-none">
                                    ${location.contact?.phone || '+994 12 409 00 00'}
                                </a>
                            </p>
                            ${distance ? `<p class="mb-1"><span class="badge bg-secondary">${distance}</span></p>` : ''}
                        </div>
                        <div class="${isMobile ? 'col-12 mt-2' : 'col-md-4 text-end'}">
                            <div class="d-grid gap-1">
                                <button class="btn btn-primary ${buttonClass}" onclick="MapManager.getDirections(${location.latitude}, ${location.longitude})">
                                    <i class="bi bi-navigation me-1"></i>
                                    ${KapitalBankApp.state.currentLanguage === 'az' ? 'İstiqamət' : 'Directions'}
                                </button>
                                ${isMobile ? `
                                    <button class="btn btn-outline-secondary ${buttonClass}" onclick="MapManager.shareLocation(${location.latitude}, ${location.longitude}, '${location.name.replace(/'/g, "\\'")}')">
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
        
        // Load initial rates and setup auto-refresh
        this.refreshCurrencyRates();
        setInterval(() => {
            this.refreshCurrencyRates();
        }, KapitalBankApp.config.updateInterval);
        
        // Setup mobile-specific features
        if (KapitalBankApp.state.touchDevice) {
            this.setupMobileCurrencyFeatures();
        }
    },
    
    setupMobileCurrencyFeatures() {
        // Add haptic feedback for currency selection
        document.querySelectorAll('#fromCurrency, #toCurrency').forEach(select => {
            select.addEventListener('change', () => {
                Utils.vibrate([25]);
            });
        });
        
        // Add swipe gesture for currency swap
        const swapButton = document.querySelector('[onclick="swapCurrencies()"]');
        if (swapButton) {
            let startX = 0;
            let startY = 0;
            
            swapButton.addEventListener('touchstart', (e) => {
                startX = e.touches[0].clientX;
                startY = e.touches[0].clientY;
            });
            
            swapButton.addEventListener('touchend', (e) => {
                const endX = e.changedTouches[0].clientX;
                const endY = e.changedTouches[0].clientY;
                const diffX = Math.abs(endX - startX);
                const diffY = Math.abs(endY - startY);
                
                // If it's a horizontal swipe, trigger swap
                if (diffX > diffY && diffX > 50) {
                    Utils.vibrate([50, 25, 50]);
                    window.swapCurrencies();
                }
            });
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
                <div class="d-flex justify-content-between align-items-center flex-wrap">
                    <div class="mb-2 mb-md-0">
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
    },
    
    chat() {
        ChatSystem.init();
        
        // Setup mobile-specific chat features
        if (KapitalBankApp.state.touchDevice) {
            this.setupMobileChatFeatures();
        }
    },
    
    setupMobileChatFeatures() {
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            // Add pull-to-refresh for chat history
            let startY = 0;
            let isRefreshing = false;
            
            chatMessages.addEventListener('touchstart', (e) => {
                if (chatMessages.scrollTop === 0) {
                    startY = e.touches[0].clientY;
                }
            });
            
            chatMessages.addEventListener('touchmove', (e) => {
                if (chatMessages.scrollTop === 0) {
                    const currentY = e.touches[0].clientY;
                    const diff = currentY - startY;
                    
                    if (diff > 50 && !isRefreshing) {
                        isRefreshing = true;
                        Utils.showAlert('info', 'Loading chat history...', 2000);
                        Utils.vibrate([50]);
                        
                        // Load more chat history if available
                        setTimeout(() => {
                            isRefreshing = false;
                        }, 1000);
                    }
                }
            });
        }
        
        // Auto-hide keyboard on scroll for iOS
        if (/iPad|iPhone|iPod/.test(navigator.userAgent)) {
            chatMessages?.addEventListener('scroll', Utils.throttle(() => {
                document.activeElement?.blur();
            }, 1000));
        }
    }
};

// Enhanced responsive design management
const ResponsiveManager = {
    breakpoints: {
        xs: 0,
        sm: 576,
        md: 768,
        lg: 992,
        xl: 1200,
        xxl: 1400
    },
    
    init() {
        this.updateDeviceInfo();
        this.setupResizeListener();
        this.setupOrientationChangeListener();
        this.optimizeForDevice();
    },
    
    updateDeviceInfo() {
        const width = window.innerWidth;
        const height = window.innerHeight;
        
        KapitalBankApp.state.isMobile = width <= this.breakpoints.md;
        KapitalBankApp.state.isTablet = width > this.breakpoints.md && width <= this.breakpoints.lg;
        KapitalBankApp.state.isDesktop = width > this.breakpoints.lg;
        
        // Update CSS custom properties
        document.documentElement.style.setProperty('--viewport-width', `${width}px`);
        document.documentElement.style.setProperty('--viewport-height', `${height}px`);
        
        // Add classes to body for CSS targeting
        document.body.classList.toggle('mobile', KapitalBankApp.state.isMobile);
        document.body.classList.toggle('tablet', KapitalBankApp.state.isTablet);
        document.body.classList.toggle('desktop', KapitalBankApp.state.isDesktop);
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
            
            // Update chat container height
            this.adjustChatHeight();
            
            // Dispatch custom event
            window.dispatchEvent(new CustomEvent('responsiveChange', {
                detail: {
                    isMobile: KapitalBankApp.state.isMobile,
                    isTablet: KapitalBankApp.state.isTablet,
                    isDesktop: KapitalBankApp.state.isDesktop
                }
            }));
        }, 250);
        
        window.addEventListener('resize', resizeHandler);
    },
    
    setupOrientationChangeListener() {
        if (KapitalBankApp.state.touchDevice) {
            window.addEventListener('orientationchange', () => {
                setTimeout(() => {
                    this.updateDeviceInfo();
                    
                    // Fix viewport height on mobile after orientation change
                    if (KapitalBankApp.state.isMobile) {
                        document.documentElement.style.setProperty('--vh', `${window.innerHeight * 0.01}px`);
                    }
                    
                    // Invalidate map
                    if (KapitalBankApp.state.map) {
                        KapitalBankApp.state.map.invalidateSize();
                    }
                }, 500);
            });
        }
    },
    
    optimizeForDevice() {
        // Reduce animations on low-end devices
        if (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 2) {
            document.documentElement.classList.add('reduced-motion');
        }
        
        // Adjust font size on very small screens
        if (window.innerWidth < 360) {
            document.documentElement.style.fontSize = '14px';
        }
        
        // Set initial viewport height for mobile
        if (KapitalBankApp.state.isMobile) {
            document.documentElement.style.setProperty('--vh', `${window.innerHeight * 0.01}px`);
        }
    },
    
    adjustChatHeight() {
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages && KapitalBankApp.state.isMobile) {
            const navHeight = document.querySelector('.navbar')?.offsetHeight || 76;
            const footerHeight = document.querySelector('footer')?.offsetHeight || 0;
            const availableHeight = window.innerHeight - navHeight - footerHeight - 200; // Extra space for input
            
            chatMessages.style.height = `${Math.max(300, availableHeight)}px`;
        }
    }
};

// Performance monitoring and optimization
const PerformanceManager = {
    metrics: {
        loadTime: 0,
        renderTime: 0,
        apiCalls: 0,
        errors: 0
    },
    
    init() {
        this.measureLoadTime();
        this.setupPerformanceObserver();
        this.optimizeForDevice();
    },
    
    measureLoadTime() {
        window.addEventListener('load', () => {
            setTimeout(() => {
                const navigation = performance.getEntriesByType('navigation')[0];
                if (navigation) {
                    this.metrics.loadTime = navigation.loadEventEnd - navigation.loadEventStart;
                    console.log(`Page load time: ${this.metrics.loadTime}ms`);
                }
            }, 0);
        });
    },
    
    setupPerformanceObserver() {
        if ('PerformanceObserver' in window) {
            try {
                const observer = new PerformanceObserver((list) => {
                    list.getEntries().forEach((entry) => {
                        if (entry.entryType === 'largest-contentful-paint') {
                            console.log(`LCP: ${entry.startTime}ms`);
                        }
                        if (entry.entryType === 'first-input') {
                            console.log(`FID: ${entry.processingStart - entry.startTime}ms`);
                        }
                    });
                });
                
                observer.observe({ entryTypes: ['largest-contentful-paint', 'first-input'] });
            } catch (e) {
                console.warn('Performance Observer not supported:', e);
            }
        }
    },
    
    optimizeForDevice() {
        // Preload critical resources
        this.preloadCriticalResources();
        
        // Setup lazy loading
        this.setupLazyLoading();
        
        // Optimize images
        this.optimizeImages();
    },
    
    preloadCriticalResources() {
        const criticalResources = [
            '/api/currency/rates',
            'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
        ];
        
        criticalResources.forEach(url => {
            if (url.startsWith('/api/')) {
                // Preload API data
                Utils.requestIdleCallback(() => {
                    Utils.apiCall(url).catch(() => {
                        // Silent fail for preloading
                    });
                });
            } else {
                // Preload external resources
                const link = document.createElement('link');
                link.rel = 'preload';
                link.href = url;
                link.as = url.endsWith('.js') ? 'script' : 'fetch';
                document.head.appendChild(link);
            }
        });
    },
    
    setupLazyLoading() {
        const observer = Utils.createIntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                        observer.unobserve(img);
                    }
                }
            });
        });
        
        if (observer) {
            document.querySelectorAll('img[data-src]').forEach(img => {
                observer.observe(img);
            });
        }
    },
    
    optimizeImages() {
        // Convert images to WebP if supported
        if ('createImageBitmap' in window) {
            document.querySelectorAll('img').forEach(img => {
                if (img.src && !img.src.includes('.webp')) {
                    const webpSrc = img.src.replace(/\.(jpg|jpeg|png)$/i, '.webp');
                    
                    // Test if WebP version exists
                    const testImg = new Image();
                    testImg.onload = () => {
                        img.src = webpSrc;
                    };
                    testImg.src = webpSrc;
                }
            });
        }
    }
};

// Application initialization
document.addEventListener('DOMContentLoaded', function() {
    console.log('🏛️ Initializing Kapital Bank AI Assistant...');
    
    // Initialize core systems
    ResponsiveManager.init();
    PerformanceManager.init();
    
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
    
    // Setup PWA features
    setupPWAFeatures();
    
    console.log('🎉 Kapital Bank AI Assistant ready!');
});

// Global event listeners
function setupGlobalEventListeners() {
    // Currency converter quick actions
    window.quickConvert = function(amount, from, to) {
        const amountField = document.getElementById('amount');
        const fromField = document.getElementById('fromCurrency');
        const toField = document.getElementById('toCurrency');
        
        if (amountField && fromField && toField) {
            amountField.value = amount;
            fromField.value = from;
            toField.value = to;
            
            PageHandlers.autoConvert();
            Utils.vibrate([50]);
        }
    };
    
    // Currency swap function
    window.swapCurrencies = function() {
        const fromSelect = document.getElementById('fromCurrency');
        const toSelect = document.getElementById('toCurrency');
        
        if (fromSelect && toSelect) {
            const fromValue = fromSelect.value;
            fromSelect.value = toSelect.value;
            toSelect.value = fromValue;
            
            PageHandlers.autoConvert();
            Utils.vibrate([50, 25, 50]);
        }
    };
    
    // Chat functions
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
        const messageInput = document.getElementById('messageInput');
        if (messageInput) {
            messageInput.value = question;
            messageInput.focus();
            
            // Auto-send for better mobile UX
            if (KapitalBankApp.state.touchDevice) {
                setTimeout(() => {
                    document.getElementById('chatForm')?.dispatchEvent(new Event('submit'));
                }, 500);
            }
        }
    };
    
    // Language management
    window.setLanguage = function(lang) {
        KapitalBankApp.state.currentLanguage = lang;
        localStorage.setItem('language', lang);
        
        const currentLangEl = document.getElementById('currentLanguage');
        if (currentLangEl) {
            currentLangEl.textContent = lang.toUpperCase();
        }
        
        // Update page content based on language
        updatePageLanguage(lang);
        
        // Dispatch language change event
        document.dispatchEvent(new CustomEvent('languageChanged', { 
            detail: { language: lang } 
        }));
        
        Utils.vibrate([25]);
    };
    
    // Load saved language
    const savedLanguage = localStorage.getItem('language') || 'en';
    if (savedLanguage !== 'en') {
        setLanguage(savedLanguage);
    }
}

// Network status monitoring
function setupNetworkMonitoring() {
    function updateOnlineStatus() {
        KapitalBankApp.state.isOnline = navigator.onLine;
        const indicator = document.getElementById('connectionStatus');
        
        if (indicator) {
            if (navigator.onLine) {
                indicator.classList.add('d-none');
                indicator.classList.remove('show');
            } else {
                indicator.classList.remove('d-none');
                indicator.classList.add('show');
            }
        }
        
        // Update API behavior based on connection
        if (!navigator.onLine) {
            // Use cached data when offline
            console.log('🔌 App is offline - using cached data');
        } else {
            // Sync pending data when back online
            console.log('🌐 App is back online');
            Utils.showAlert('success', 'Connection restored', 2000);
        }
    }
    
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
    
    // Initial check
    updateOnlineStatus();
}

// Accessibility features
function setupAccessibilityFeatures() {
    // Skip link focus management
    const skipLink = document.querySelector('.sr-only-focusable');
    if (skipLink) {
        skipLink.addEventListener('click', (e) => {
            e.preventDefault();
            const target = document.querySelector(skipLink.getAttribute('href'));
            if (target) {
                target.focus();
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    }
    
    // Keyboard navigation enhancement
    document.addEventListener('keydown', (e) => {
        // Global shortcuts
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
            
            // Clear search/input focus
            if (document.activeElement?.tagName === 'INPUT') {
                document.activeElement.blur();
            }
        }
    });
    
    // Enhanced focus management
    document.addEventListener('focusin', (e) => {
        // Add visual focus indicators
        e.target.classList.add('focused');
    });
    
    document.addEventListener('focusout', (e) => {
        e.target.classList.remove('focused');
    });
    
    // Screen reader announcements for dynamic content
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        // Announce new alerts
                        if (node.classList?.contains('alert')) {
                            const text = node.textContent?.trim();
                            if (text) {
                                Utils.announceToScreenReader(text);
                            }
                        }
                    }
                });
            }
        });
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
}

// PWA features
function setupPWAFeatures() {
    // Service worker registration
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register('/static/sw.js')
                .then((registration) => {
                    console.log('🔧 Service Worker registered:', registration);
                    
                    // Check for updates
                    registration.addEventListener('updatefound', () => {
                        const newWorker = registration.installing;
                        if (newWorker) {
                            newWorker.addEventListener('statechange', () => {
                                if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                                    Utils.showAlert('info', 'App update available. Refresh to update.', 0);
                                }
                            });
                        }
                    });
                })
                .catch((error) => {
                    console.warn('Service Worker registration failed:', error);
                });
        });
    }
    
    // Install prompt handling
    let deferredPrompt;
    
    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        deferredPrompt = e;
        
        // Show install button/banner
        showInstallPrompt();
    });
    
    function showInstallPrompt() {
        if (KapitalBankApp.state.touchDevice && deferredPrompt) {
            const installHTML = `
                <div class="alert alert-info alert-dismissible fade show" role="alert">
                    <i class="bi bi-download me-2"></i>
                    Install Kapital Bank AI Assistant for quick access!
                    <button type="button" class="btn btn-sm btn-outline-primary ms-2" onclick="installPWA()">
                        Install
                    </button>
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            `;
            
            const alertContainer = document.getElementById('alertContainer');
            if (alertContainer) {
                alertContainer.insertAdjacentHTML('beforeend', installHTML);
            }
        }
    }
    
    window.installPWA = function() {
        if (deferredPrompt) {
            deferredPrompt.prompt();
            deferredPrompt.userChoice.then((choiceResult) => {
                if (choiceResult.outcome === 'accepted') {
                    console.log('PWA installed');
                    Utils.vibrate([100, 50, 100]);
                }
                deferredPrompt = null;
            });
        }
    };
    
    // Handle app installation
    window.addEventListener('appinstalled', () => {
        console.log('PWA was installed');
        Utils.showAlert('success', 'App installed successfully!', 3000);
        deferredPrompt = null;
    });
}

// Language update function
function updatePageLanguage(lang) {
    // Update static text elements based on language
    const translations = {
        'en': {
            'loading': 'Loading...',
            'search': 'Search',
            'directions': 'Directions',
            'share': 'Share',
            'clear_chat': 'Clear Chat',
            'your_location': 'Your Location'
        },
        'az': {
            'loading': 'Yüklənir...',
            'search': 'Axtar',
            'directions': 'İstiqamət',
            'share': 'Paylaş',
            'clear_chat': 'Söhbəti Təmizlə',
            'your_location': 'Sizin Məkanınız'
        }
    };
    
    const t = translations[lang] || translations['en'];
    
    // Update loading text
    const loadingText = document.getElementById('loadingText');
    if (loadingText && loadingText.textContent === translations['en']['loading']) {
        loadingText.textContent = t['loading'];
    }
    
    // Update other translatable elements
    document.querySelectorAll('[data-translate]').forEach(element => {
        const key = element.dataset.translate;
        if (t[key]) {
            element.textContent = t[key];
        }
    });
}

// Export for external use
window.KapitalBankApp = KapitalBankApp;
window.Utils = Utils;
window.LocationService = LocationService;
window.MapManager = MapManager;
window.CurrencyService = CurrencyService;
window.ChatSystem = ChatSystem;
window.PageHandlers = PageHandlers;
window.ResponsiveManager = ResponsiveManager;/**
 * Kapital Bank AI Assistant - Enhanced Frontend JavaScript
 * Mobile-first, accessible, and performance-optimized
 */

// Global application state with better mobile support
window.KapitalBankApp = {
    config: {
        defaultLocation: [40.4093, 49.8671], // Baku center
        mapZoom: 12,
        mobileMapZoom: 11,
        searchRadius: 5,
        apiBaseUrl: window.location.origin,
        updateInterval: 300000, // 5 minutes
        debounceDelay: 300,
        mobileBreakpoint: 768,
        maxRetries: 3,
        requestTimeout: 30000
    },
    
    state: {
        currentLocation: null,
        map: null,
        markers: [],
        currentLanguage: localStorage.getItem('language') || 'en',
        isOnline: navigator.onLine,
        lastUpdate: null,
        isMobile: window.innerWidth <= 768,
        touchDevice: 'ontouchstart' in window,
        isLoading: false,
        cache: new Map()
    },
    
    features: {
        geolocation: 'geolocation' in navigator,
        notifications: 'Notification' in window,
        serviceWorker: 'serviceWorker' in navigator,
        intersectionObserver: 'IntersectionObserver' in window,
        webgl: (() => {
            try {
                const canvas = document.createElement('canvas');
                return !!(window.WebGLRenderingContext && canvas.getContext('webgl'));
            } catch (e) {
                return false;
            }
        })()
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
            // Use more mobile-friendly precision on small screens
            const finalPrecision = KapitalBankApp.state.isMobile ? Math.min(precision, 2) : precision;
            
            return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: currency,
                minimumFractionDigits: finalPrecision,
                maximumFractionDigits: finalPrecision
            }).format(amount);
        } catch (error) {
            // Fallback for unsupported currencies
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
        const isDismissible = duration > 0;
        
        const alertHTML = `
            <div id="${alertId}" class="alert alert-${type} ${isDismissible ? 'alert-dismissible' : ''} fade show" role="alert">
                <i class="bi bi-${this.getAlertIcon(type)} me-2" aria-hidden="true"></i>
                <span>${message}</span>
                ${isDismissible ? '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>' : ''}
            </div>
        `;
        
        alertContainer.insertAdjacentHTML('beforeend', alertHTML);
        
        // Auto-remove if duration is specified
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
        
        // Announce to screen readers
        this.announceToScreenReader(message);
    },
    
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
        const cacheKey = `${endpoint}-${JSON.stringify(options)}`;
        
        // Check cache for GET requests
        if (!options.method || options.method === 'GET') {
            const cached = KapitalBankApp.state.cache.get(cacheKey);
            if (cached && Date.now() - cached.timestamp < 300000) { // 5 minutes cache
                return cached.data;
            }
        }
        
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), KapitalBankApp.config.requestTimeout);
            
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
            
            const data = await response.json();
            
            // Cache successful GET requests
            if (!options.method || options.method === 'GET') {
                KapitalBankApp.state.cache.set(cacheKey, {
                    data,
                    timestamp: Date.now()
                });
            }
            
            return data;
            
        } catch (error) {
            if (error.name === 'AbortError') {
                throw new Error('Request timed out. Please check your connection and try again.');
            }
            
            console.error(`API call failed for ${endpoint}:`, error);
            throw error;
        }
    },
    
    // Mobile-specific utilities
    isMobileDevice() {
        return KapitalBankApp.state.isMobile || KapitalBankApp.state.touchDevice;
    },
    
    vibrate(pattern = [100]) {
        if ('vibrate' in navigator && KapitalBankApp.state.touchDevice) {
            navigator.vibrate(pattern);
        }
    },
    
    preventZoom(element) {
        if (KapitalBankApp.state.touchDevice) {
            element.addEventListener('touchstart', function(e) {
                if (e.touches.length > 1) {
                    e.preventDefault();
                }
            });
        }
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
    },
    
    // Performance utilities
    requestIdleCallback(callback, options = {}) {
        if ('requestIdleCallback' in window) {
            return window.requestIdleCallback(callback, options);
        } else {
            return setTimeout(callback, 1);
        }
    },
    
    // Intersection Observer for lazy loading
    createIntersectionObserver(callback, options = {}) {
        if (KapitalBankApp.features.intersectionObserver) {
            return new IntersectionObserver(callback, {
                rootMargin: '50px',
                threshold: 0.1,
                ...options
            });
        }
        return null;
    }
};

// Enhanced location service with better mobile support
const LocationService = {
    watchId: null,
    
    async getCurrentLocation(options = {}) {
        return new Promise((resolve, reject) => {
            if (!KapitalBankApp.features.geolocation) {
                console.warn('Geolocation not supported');
                const defaultLocation = KapitalBankApp.config.defaultLocation;
                KapitalBankApp.state.currentLocation = defaultLocation;
                resolve(defaultLocation);
                return;
            }
            
            const defaultOptions = {
                enableHighAccuracy: !KapitalBankApp.state.isMobile, // Less accurate but faster on mobile
                timeout: KapitalBankApp.state.isMobile ? 15000 : 10000, // Longer timeout on mobile
                maximumAge: 300000 // 5 minutes
            };
            
            const finalOptions = { ...defaultOptions, ...options };
            
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
                finalOptions
            );
        });
    },
    
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
    
    startWatchingLocation(callback, options = {}) {
        if (!KapitalBankApp.features.geolocation) return null;
        
        if (this.watchId) {
            navigator.geolocation.clearWatch(this.watchId);
        }
        
        const watchOptions = {
            enableHighAccuracy: false, // Save battery
            timeout: 20000,
            maximumAge: 60000, // 1 minute
            ...options
        };
        
        this.watchId = navigator.geolocation.watchPosition(
            position => {
                const location = [position.coords.latitude, position.coords.longitude];
                KapitalBankApp.state.currentLocation = location;
                callback(location, null);
            },
            error => {
                console.warn('Location watch error:', error);
                callback(null, error);
            },
            watchOptions
        );
        
        return this.watchId;
    },
    
    stopWatchingLocation() {
        if (this.watchId) {
            navigator.geolocation.clearWatch(this.watchId);
            this.watchId = null;
        }
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

// Enhanced map manager with mobile optimizations
const MapManager = {
    initMap(containerId, center = null, options = {}) {
        const mapCenter = center || KapitalBankApp.state.currentLocation || KapitalBankApp.config.defaultLocation;
        const isMobile = KapitalBankApp.state.isMobile;
        
        const defaultOptions = {
            zoomControl: !isMobile, // Hide zoom control on mobile to save space
            attributionControl: !isMobile,
            scrollWheelZoom: !isMobile,
            doubleClickZoom: true,
            touchZoom: isMobile,
            dragging: true,
            tap: isMobile,
            maxZoom: 18,
            minZoom: isMobile ? 10 : 8
        };
        
        const finalOptions = { ...defaultOptions, ...options };
        const zoom = isMobile ? KapitalBankApp.config.mobileMapZoom : KapitalBankApp.config.mapZoom;
        
        const map = L.map(containerId, finalOptions).setView(mapCenter, zoom);
        
        // Use different tile layer based on device capabilities
        const tileUrl = KapitalBankApp.features.webgl 
            ? 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
            : 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
            
        L.tileLayer(tileUrl, {
            attribution: isMobile ? '' : '© OpenStreetMap contributors',
            maxZoom: 18,
            loading: 'lazy' // Lazy load tiles
        }).addTo(map);
        
        // Add mobile-specific controls
        if (isMobile) {
            this.addMobileControls(map);
        }
        
        // Handle map resize
        this.setupResponsiveMap(map);
        
        KapitalBankApp.state.map = map;
        return map;
    },
    
    addMobileControls(map) {
        // Add locate button
        const locateControl = L.control({ position: 'topright' });
        locateControl.onAdd = function() {
            const div = L.DomUtil.create('div', 'leaflet-bar leaflet-control leaflet-control-custom');
            div.innerHTML = '<button class="btn btn-light btn-sm" onclick="MapManager.centerOnUser()" title="Center on my location"><i class="bi bi-crosshair"></i></button>';
            div.style.backgroundColor = 'white';
            div.style.padding = '5px';
            div.style.borderRadius = '4px';
            return div;
        };
        locateControl.addTo(map);
        
        // Add fullscreen toggle for mobile
        const fullscreenControl = L.control({ position: 'topright' });
        fullscreenControl.onAdd = function() {
            const div = L.DomUtil.create('div', 'leaflet-bar leaflet-control leaflet-control-custom');
            div.innerHTML = '<button class="btn btn-light btn-sm" onclick="MapManager.toggleFullscreen()" title="Toggle fullscreen"><i class="bi bi-arrows-fullscreen"></i></button>';
            div.style.backgroundColor = 'white';
            div.style.padding = '5px';
            div.style.borderRadius = '4px';
            return div;
        };
        fullscreenControl.addTo(map);
    },
    
    setupResponsiveMap(map) {
        const resizeObserver = new ResizeObserver(Utils.throttle(() => {
            map.invalidateSize();
        }, 250));
        
        const mapContainer = map.getContainer();
        resizeObserver.observe(mapContainer);
        
        // Handle orientation change on mobile
        if (KapitalBankApp.state.touchDevice) {
            window.addEventListener('orientationchange', () => {
                setTimeout(() => {
                    map.invalidateSize();
                }, 500);
            });
        }
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
            
            // Use different popup options for mobile
            const popupOptions = isMobile ? {
                maxWidth: 250,
                closeButton: true,
                autoClose: true,
                keepInView: true
            } : {
                maxWidth: 300,
                closeButton: true
            };
            
            marker.bindPopup(popupContent, popupOptions);
            
            // Add click event for mobile
            if (isMobile) {
                marker.on('click', () => {
                    Utils.vibrate([50]); // Haptic feedback
                });
            }
            
            markers.push(marker);
        });
        
        KapitalBankApp.state.markers = markers;
        
        // Fit bounds if multiple markers
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
            html: `<div style="
                background-color: ${config.color}; 
                border-radius: 50%; 
                width: ${size}px; 
                height: ${size}px; 
                display: flex; 
                align-items: center; 
                justify-content: center; 
                border: 2px solid white; 
                box-shadow: 0 2px 5px rgba(0,0,0,0.3);
                font-size: ${fontSize};
            ">
                <span>${config.icon}</span>
            </div>`,
            className: 'custom-div-icon',
            iconSize: [size, size],
            iconAnchor: [size/2, size/2]
        });
    },
    
    createPopupContent(location, isMobile = false) {
        const distance = location.distance_km ? `<br><small class="text-muted">📍 ${Utils.formatDistance(location.distance_km)} away</small>` : '';
        const buttonClass = isMobile ? 'btn-sm' : 'btn-sm';
        
        return `
            <div class="map-popup">
                <h6 class="mb-1">${location.name}</h6>
                <p class="mb-1 small">${location.address}</p>
                <p class="mb-1 small"><strong>📞</strong> ${location.contact?.phone || '+994 12 409 00 00'}</p>
                ${distance}
                <div class="mt-2 d-grid gap-1">
                    <button class="btn btn-primary ${buttonClass}" onclick="MapManager.getDirections(${location.latitude}, ${location.longitude})">
                        <i class="bi bi-navigation me-1"></i>Directions
                    </button>
                    ${isMobile ? `
                        <button class="btn btn-outline-secondary ${buttonClass}" onclick="MapManager.shareLocation(${location.latitude}, ${location.longitude}, '${location.name}')">
                            <i class="bi bi-share me-1"></i>Share
                        </button>
                    ` : ''}
                </div>
            </div>
        `;
    },
    
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
    
    toggleFullscreen() {
        const mapContainer = document.querySelector('#map').closest('.card');
        if (mapContainer) {
            mapContainer.classList.toggle('fullscreen-map');
            
            // Update map size after transition
            setTimeout(() => {
                if (KapitalBankApp.state.map) {
                    KapitalBankApp.state.map.invalidateSize();
                }
            }, 300);
            
            Utils.vibrate([50]); // UI feedback
        }
    },
    
    getDirections(lat, lng) {
        const userLocation = KapitalBankApp.state.currentLocation;
        
        // For mobile devices, try to open native maps app
        if (KapitalBankApp.state.touchDevice) {
            const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
            const isAndroid = /Android/.test(navigator.userAgent);
            
            if (isIOS) {
                const url = userLocation 
                    ? `http://maps.apple.com/?saddr=${user