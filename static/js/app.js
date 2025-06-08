// static/js/app.js

// Geolocation Manager
class GeolocationManager {
    constructor() {
        this.location = null;
        this.error = null;
        this.watchId = null;
    }

    async init() {
        if (!navigator.geolocation) {
            this.error = 'Geolocation is not supported by your browser';
            return false;
        }

        return new Promise((resolve) => {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    this.location = {
                        lat: position.coords.latitude,
                        lng: position.coords.longitude,
                        accuracy: position.coords.accuracy,
                        timestamp: new Date().toISOString()
                    };
                    this.cacheLocation();
                    resolve(true);
                },
                (error) => {
                    this.error = error.message;
                    this.loadCachedLocation();
                    resolve(false);
                },
                {
                    enableHighAccuracy: true,
                    timeout: 5000,
                    maximumAge: 300000 // 5 minutes
                }
            );
        });
    }

    startWatching() {
        if (!navigator.geolocation) return;

        this.watchId = navigator.geolocation.watchPosition(
            (position) => {
                this.location = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude,
                    accuracy: position.coords.accuracy,
                    timestamp: new Date().toISOString()
                };
                this.cacheLocation();
            },
            (error) => {
                console.error('Location watch error:', error);
            },
            {
                enableHighAccuracy: false,
                timeout: 10000,
                maximumAge: 300000
            }
        );
    }

    stopWatching() {
        if (this.watchId) {
            navigator.geolocation.clearWatch(this.watchId);
            this.watchId = null;
        }
    }

    cacheLocation() {
        if (this.location) {
            sessionStorage.setItem('userLocation', JSON.stringify(this.location));
        }
    }

    loadCachedLocation() {
        const cached = sessionStorage.getItem('userLocation');
        if (cached) {
            this.location = JSON.parse(cached);
        }
    }

    getLocation() {
        return this.location;
    }
}

// Chat Application
class ChatApp {
    constructor() {
        this.geoManager = new GeolocationManager();
        this.isLoading = false;
        this.messageInput = document.getElementById('message-input');
        this.chatForm = document.getElementById('chat-form');
        this.chatMessages = document.getElementById('chat-messages');
        this.locationStatus = document.getElementById('location-status');
        this.locationText = document.getElementById('location-text');
        
        this.init();
    }

    async init() {
        // Initialize geolocation
        const locationSuccess = await this.geoManager.init();
        this.updateLocationStatus(locationSuccess);
        
        // Start watching location
        this.geoManager.startWatching();
        
        // Set up event listeners
        this.chatForm.addEventListener('submit', (e) => this.handleSubmit(e));
        
        // Focus on input
        this.messageInput.focus();
    }

    updateLocationStatus(success) {
        if (success) {
            this.locationStatus.classList.add('location-active');
            this.locationText.textContent = 'Location detected';
        } else {
            this.locationStatus.classList.add('location-error');
            this.locationText.textContent = 'Location unavailable';
        }
    }

    detectLocationContext(message) {
        const locationKeywords = [
            'nearest', 'closest', 'near me', 'branch', 'atm', 'location',
            'where', 'find', 'address', 'hours', 'open', 'distance',
            'directions', 'navigate', 'how far', 'nearby'
        ];
        
        const lowerMessage = message.toLowerCase();
        return locationKeywords.some(keyword => lowerMessage.includes(keyword));
    }

    async handleSubmit(e) {
        e.preventDefault();
        
        if (this.isLoading || !this.messageInput.value.trim()) return;
        
        const message = this.messageInput.value.trim();
        this.addMessage(message, true);
        this.messageInput.value = '';
        
        // Show loading
        this.showLoading();
        
        try {
            const isLocationQuery = this.detectLocationContext(message);
            const location = this.geoManager.getLocation();
            
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    context: {
                        hasLocation: !!location,
                        isLocationQuery: isLocationQuery,
                        userLocation: location
                    }
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.hideLoading();
            
            // Add bot response
            this.addBotMessage(data);
            
        } catch (error) {
            console.error('Error:', error);
            this.hideLoading();
            this.addMessage('I apologize, but I encountered an error. Please try again.', false);
        }
    }

    addMessage(text, isUser) {
        const template = isUser ? 
            document.getElementById('user-message-template') : 
            document.getElementById('bot-message-template');
        
        const messageEl = template.content.cloneNode(true);
        messageEl.querySelector('p').textContent = text;
        
        this.chatMessages.appendChild(messageEl);
        this.scrollToBottom();
    }

    addBotMessage(data) {
        const template = document.getElementById('bot-message-template');
        const messageEl = template.content.cloneNode(true);
        const contentDiv = messageEl.querySelector('.message-content');
        
        // Add main message
        const p = document.createElement('p');
        p.textContent = data.message;
        contentDiv.appendChild(p);
        
        // Add branch info if available
        if (data.branchInfo) {
            const branchTemplate = document.getElementById('branch-info-template');
            const branchEl = branchTemplate.content.cloneNode(true);
            
            branchEl.querySelector('.location-name').textContent = data.branchInfo.name;
            branchEl.querySelector('.location-distance span').textContent = `${data.branchInfo.distance} km`;
            branchEl.querySelector('.location-address span').textContent = data.branchInfo.address;
            branchEl.querySelector('.location-hours span').textContent = data.branchInfo.hours;
            
            contentDiv.appendChild(branchEl);
        }
        
        // Add ATM info if available
        if (data.atmInfo && data.atmInfo.length > 0) {
            const atmTemplate = document.getElementById('atm-info-template');
            const atmEl = atmTemplate.content.cloneNode(true);
            const atmList = atmEl.querySelector('.atm-list');
            
            data.atmInfo.forEach(atm => {
                const itemTemplate = document.getElementById('atm-item-template');
                const itemEl = itemTemplate.content.cloneNode(true);
                
                itemEl.querySelector('.atm-location').textContent = `${atm.location} (${atm.distance.toFixed(1)} km)`;
                const statusEl = itemEl.querySelector('.atm-status');
                statusEl.textContent = atm.status;
                statusEl.className = `atm-status ${atm.status === 'Operational' ? 'status-operational' : 'status-offline'}`;
                
                atmList.appendChild(itemEl);
            });
            
            contentDiv.appendChild(atmEl);
        }
        
        this.chatMessages.appendChild(messageEl);
        this.scrollToBottom();
    }

    showLoading() {
        this.isLoading = true;
        const loadingTemplate = document.getElementById('loading-template');
        const loadingEl = loadingTemplate.content.cloneNode(true);
        loadingEl.firstElementChild.id = 'loading-message';
        this.chatMessages.appendChild(loadingEl);
        this.scrollToBottom();
    }

    hideLoading() {
        this.isLoading = false;
        const loadingMessage = document.getElementById('loading-message');
        if (loadingMessage) {
            loadingMessage.remove();
        }
    }

    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new ChatApp();
});