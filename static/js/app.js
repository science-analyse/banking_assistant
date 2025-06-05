// Main JavaScript for AI Banking Assistant

// Global variables
let currentLanguage = 'en';
let chatHistory = [];
let loadingModal;

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Initialize Bootstrap components
    loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'), {
        backdrop: 'static',
        keyboard: false
    });
    
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
            initializeChat();
            break;
        case '/currency':
            initializeCurrencyConverter();
            break;
    }
    
    // Initialize common features
    initializeAlerts();
    initializeFormValidation();
}

// Language Management
function setLanguage(lang) {
    currentLanguage = lang;
    localStorage.setItem('language', lang);
    
    // Update UI text based on language
    updateLanguageText();
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
    
    // Update loading text
    const loadingText = document.getElementById('loadingText');
    if (loadingText) {
        loadingText.textContent = translations[currentLanguage].loading;
    }
}

// API Helper Functions
async function apiCall(endpoint, method = 'GET', data = null) {
    try {
        showLoading();
        
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            }
        };
        
        if (data && method !== 'GET') {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(endpoint, options);
        const result = await response.json();
        
        hideLoading();
        
        if (!response.ok) {
            throw new Error(result.detail || 'API Error');
        }
        
        return result;
    } catch (error) {
        hideLoading();
        showAlert('error', error.message);
        throw error;
    }
}

function showLoading(text = null) {
    if (text) {
        document.getElementById('loadingText').textContent = text;
    }
    loadingModal.show();
}

function hideLoading() {
    loadingModal.hide();
}

// Alert System
function initializeAlerts() {
    // Auto-hide alerts after 5 seconds
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
    const alertId = 'alert-' + Date.now();
    
    const alertHtml = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
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
}

// Form Validation
function initializeFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                showAlert('danger', 'Please fill in all required fields correctly.');
            }
            form.classList.add('was-validated');
        });
    });
}

// Loan Comparison Functions
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
            const result = await apiCall('/api/loans/compare', 'POST', loanData);
            displayLoanResults(result);
        } catch (error) {
            console.error('Loan comparison error:', error);
        }
    });
}

function displayLoanResults(results) {
    const container = document.getElementById('loanResults');
    if (!container) return;
    
    let html = `
        <div class="row mb-4">
            <div class="col-12">
                <h3>Loan Comparison Results</h3>
                <p class="text-muted">Found ${results.total_banks} options for ${results.loan_amount} ${results.currency} ${results.loan_type} loan</p>
            </div>
        </div>
    `;
    
    if (results.best_rate) {
        html += `
            <div class="row mb-4">
                <div class="col-12">
                    <div class="loan-result-card best-rate fade-in">
                        <h4 class="text-success mb-3">
                            <i class="bi bi-trophy me-2"></i>
                            Best Rate: ${results.best_rate.bank_name}
                        </h4>
                        <div class="row">
                            <div class="col-md-3">
                                <h5 class="text-primary">${results.best_rate.avg_interest_rate}%</h5>
                                <small class="text-muted">Interest Rate</small>
                            </div>
                            <div class="col-md-3">
                                <h5>${results.best_rate.monthly_payment} ${results.currency}</h5>
                                <small class="text-muted">Monthly Payment</small>
                            </div>
                            <div class="col-md-3">
                                <h5>${results.best_rate.total_payment} ${results.currency}</h5>
                                <small class="text-muted">Total Payment</small>
                            </div>
                            <div class="col-md-3">
                                <a href="tel:${results.best_rate.phone}" class="btn btn-success">
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
    
    // Chart data preparation
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
                    <div class="mt-3 d-flex gap-2">
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
    setTimeout(() => {
        const ctx = document.getElementById('loanChart');
        if (ctx) {
            new Chart(ctx, {
                type: 'bar',
                data: chartData,
                options: {
                    responsive: true,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Interest Rates Comparison'
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
    }, 100);
}

// Branch Finder Functions
function initializeBranchFinder() {
    const branchForm = document.getElementById('branchFinderForm');
    if (!branchForm) return;
    
    // Initialize map
    const map = L.map('branchMap').setView([40.4093, 49.8671], 12);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    
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
            const result = await apiCall('/api/branches/find', 'POST', searchData);
            displayBranchResults(result, map);
        } catch (error) {
            console.error('Branch finder error:', error);
        }
    });
    
    // Get user location
    document.getElementById('useMyLocation')?.addEventListener('click', function() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(function(position) {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;
                
                document.getElementById('latitude').value = lat.toFixed(6);
                document.getElementById('longitude').value = lng.toFixed(6);
                
                map.setView([lat, lng], 13);
                showAlert('success', 'Location updated successfully!');
            }, function(error) {
                showAlert('warning', 'Unable to get your location. Using default location (Baku).');
            });
        }
    });
}

function displayBranchResults(results, map) {
    const container = document.getElementById('branchResults');
    if (!container) return;
    
    // Clear existing markers
    map.eachLayer(layer => {
        if (layer instanceof L.Marker) {
            map.removeLayer(layer);
        }
    });
    
    let html = `
        <div class="row mb-4">
            <div class="col-12">
                <h3>Found ${results.showing} branches nearby</h3>
                <p class="text-muted">Showing closest branches within range</p>
            </div>
        </div>
        <div class="row">
    `;
    
    results.branches.forEach((branch, index) => {
        // Add marker to map
        const marker = L.marker([branch.coordinates.lat, branch.coordinates.lng])
            .addTo(map)
            .bindPopup(`
                <strong>${branch.bank_name}</strong><br>
                ${branch.branch_name}<br>
                <small>${branch.address}</small><br>
                <strong>${branch.distance_km} km away</strong>
            `);
        
        html += `
            <div class="col-lg-6 mb-3">
                <div class="branch-card slide-up" style="animation-delay: ${index * 0.1}s">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h5 class="mb-1">${branch.bank_name}</h5>
                        <span class="badge bg-success">${branch.distance_km} km</span>
                    </div>
                    <h6 class="text-primary mb-2">${branch.branch_name}</h6>
                    <p class="text-muted mb-2">
                        <i class="bi bi-geo-alt me-1"></i>
                        ${branch.address}
                    </p>
                    <div class="row text-sm">
                        <div class="col-6">
                            <small>
                                <i class="bi bi-clock me-1"></i>
                                ${branch.hours}
                            </small>
                        </div>
                        <div class="col-6">
                            <small>
                                <i class="bi bi-telephone me-1"></i>
                                ${branch.phone}
                            </small>
                        </div>
                    </div>
                    <div class="mt-3 d-flex gap-2">
                        <button class="btn btn-primary btn-sm" onclick="focusOnBranch(${branch.coordinates.lat}, ${branch.coordinates.lng})">
                            <i class="bi bi-geo-alt me-1"></i>View on Map
                        </button>
                        <a href="tel:${branch.phone}" class="btn btn-outline-primary btn-sm">
                            <i class="bi bi-telephone me-1"></i>Call
                        </a>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
    
    // Fit map to show all branches
    if (results.branches.length > 0) {
        const group = new L.featureGroup(map._layers);
        map.fitBounds(group.getBounds().pad(0.1));
    }
}

function focusOnBranch(lat, lng) {
    // This function will be called from the branch cards
    const map = window.branchMap || L.map('branchMap');
    map.setView([lat, lng], 16);
}

// Chat Functions
function initializeChat() {
    const chatContainer = document.getElementById('chatMessages');
    const chatForm = document.getElementById('chatForm');
    const messageInput = document.getElementById('messageInput');
    
    if (!chatForm) return;
    
    // Load chat history
    loadChatHistory();
    
    chatForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const message = messageInput.value.trim();
        if (!message) return;
        
        // Add user message to chat
        addMessageToChat('user', message);
        messageInput.value = '';
        
        // Show typing indicator
        showTypingIndicator();
        
        try {
            const response = await apiCall('/api/chat', 'POST', {
                message: message,
                language: currentLanguage,
                session_id: generateSessionId()
            });
            
            hideTypingIndicator();
            addMessageToChat('assistant', response.response);
            
            // Show suggestions if available
            if (response.suggestions) {
                showSuggestions(response.suggestions);
            }
            
        } catch (error) {
            hideTypingIndicator();
            addMessageToChat('assistant', 'Sorry, I encountered an error. Please try again.');
        }
    });
    
    // Clear chat button
    document.getElementById('clearChat')?.addEventListener('click', function() {
        clearChat();
    });
}

function addMessageToChat(sender, message) {
    const chatContainer = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender} fade-in`;
    
    const time = new Date().toLocaleTimeString();
    messageDiv.innerHTML = `
        <div class="d-flex justify-content-between align-items-start mb-1">
            <strong>${sender === 'user' ? 'You' : 'AI Assistant'}</strong>
            <small class="opacity-75">${time}</small>
        </div>
        <div>${message}</div>
    `;
    
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    // Save to history
    chatHistory.push({ sender, message, time });
    saveChatHistory();
}

function showTypingIndicator() {
    const chatContainer = document.getElementById('chatMessages');
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
}

function hideTypingIndicator() {
    const typingIndicator = document.getElementById('typingIndicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

function showSuggestions(suggestions) {
    const suggestionsContainer = document.getElementById('suggestions');
    if (!suggestionsContainer) return;
    
    let html = '<div class="d-flex flex-wrap gap-2 mt-3">';
    suggestions.forEach(suggestion => {
        html += `
            <button class="btn btn-outline-primary btn-sm" onclick="sendSuggestion('${suggestion}')">
                ${suggestion}
            </button>
        `;
    });
    html += '</div>';
    
    suggestionsContainer.innerHTML = html;
}

function sendSuggestion(suggestion) {
    document.getElementById('messageInput').value = suggestion;
    document.getElementById('chatForm').dispatchEvent(new Event('submit'));
}

function clearChat() {
    document.getElementById('chatMessages').innerHTML = '';
    document.getElementById('suggestions').innerHTML = '';
    chatHistory = [];
    localStorage.removeItem('chatHistory');
}

function loadChatHistory() {
    const saved = localStorage.getItem('chatHistory');
    if (saved) {
        chatHistory = JSON.parse(saved);
        chatHistory.forEach(msg => {
            const chatContainer = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `chat-message ${msg.sender}`;
            messageDiv.innerHTML = `
                <div class="d-flex justify-content-between align-items-start mb-1">
                    <strong>${msg.sender === 'user' ? 'You' : 'AI Assistant'}</strong>
                    <small class="opacity-75">${msg.time}</small>
                </div>
                <div>${msg.message}</div>
            `;
            chatContainer.appendChild(messageDiv);
        });
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
}

function saveChatHistory() {
    localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
}

function generateSessionId() {
    let sessionId = localStorage.getItem('chatSessionId');
    if (!sessionId) {
        sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('chatSessionId', sessionId);
    }
    return sessionId;
}

// Currency Converter Functions
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
            const rates = await apiCall('/api/currency/rates');
            const result = convertCurrency(amount, fromCurrency, toCurrency, rates.rates);
            displayConversionResult(amount, fromCurrency, result, toCurrency);
        } catch (error) {
            console.error('Currency conversion error:', error);
        }
    });
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

function displayConversionResult(amount, fromCurrency, result, toCurrency) {
    const container = document.getElementById('conversionResult');
    if (!container) return;
    
    container.innerHTML = `
        <div class="converter-result fade-in">
            <i class="bi bi-currency-exchange display-6 mb-3"></i>
            <h3>${amount} ${fromCurrency} = ${result.toFixed(2)} ${toCurrency}</h3>
            <small>Conversion completed at ${new Date().toLocaleString()}</small>
        </div>
    `;
}

// Utility Functions
function formatCurrency(amount, currency = 'AZN') {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency,
        minimumFractionDigits: 2
    }).format(amount);
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

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

// Export functions for global access
window.apiCall = apiCall;
window.showAlert = showAlert;
window.setLanguage = setLanguage;
window.focusOnBranch = focusOnBranch;
window.sendSuggestion = sendSuggestion;
window.clearChat = clearChat;