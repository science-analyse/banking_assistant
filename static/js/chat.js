/**
 * Enhanced RAG Chat Interface
 * Handles AI conversations with real-time banking data
 */

class RAGChatInterface {
    constructor() {
        this.chatContainer = document.getElementById('chat-messages');
        this.messageInput = document.getElementById('message-input');
        this.sendButton = document.getElementById('send-button');
        this.languageSelect = document.getElementById('language-select');
        this.typingIndicator = document.getElementById('typing-indicator');
        
        this.isTyping = false;
        this.currentLanguage = 'en';
        
        this.initializeEventListeners();
        this.addWelcomeMessage();
        this.loadSuggestedQuestions();
    }
    
    initializeEventListeners() {
        // Send message on button click
        this.sendButton?.addEventListener('click', () => this.handleSendMessage());
        
        // Send message on Enter key
        this.messageInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSendMessage();
            }
        });
        
        // Language change
        this.languageSelect?.addEventListener('change', (e) => {
            this.currentLanguage = e.target.value;
            this.addSystemMessage(
                this.currentLanguage === 'az' 
                    ? 'Dil azərbaycanca olaraq dəyişdirildi.' 
                    : 'Language changed to English.'
            );
        });
        
        // Auto-resize textarea
        this.messageInput?.addEventListener('input', () => this.autoResizeTextarea());
    }
    
    addWelcomeMessage() {
        const welcomeMessages = {
            en: `👋 Welcome to your AI Banking Assistant!\n\nI can help you with:
• Current exchange rates from CBAR
• Finding bank branches and ATMs
• Banking service information
• Currency conversion
\nTry asking: "What's the current USD rate?" or "Find ATMs near me"`,
            az: `👋 AI Bank Köməkçinizə xoş gəlmisiniz!\n\nMən sizə kömək edə bilərəm:
• AMB-nin cari məzənnələri
• Bank filialları və bankomatları tapmaq
• Bank xidmətləri haqqında məlumat
• Valyuta çevrilməsi
\nSınayın: "Hazırki USD məzənnəsi nədir?" və ya "Yaxınımda bankomatları tap"`
        };
        
        this.addMessage('assistant', welcomeMessages[this.currentLanguage]);
    }
    
    loadSuggestedQuestions() {
        const suggestions = {
            en: [
                "What's the current USD exchange rate?",
                "Find bank branches near me",
                "Convert 100 USD to AZN", 
                "What are the banking hours?",
                "Show me ATM locations"
            ],
            az: [
                "Hazırki USD məzənnəsi nədir?",
                "Yaxınımda bank filialları tap",
                "100 USD-ni AZN-ə çevir",
                "Bank saatları nədir?", 
                "Bankomat yerlərini göstər"
            ]
        };
        
        this.addSuggestedQuestions(suggestions[this.currentLanguage]);
    }
    
    addSuggestedQuestions(questions) {
        const suggestionsContainer = document.createElement('div');
        suggestionsContainer.className = 'suggested-questions mt-3';
        suggestionsContainer.innerHTML = `
            <small class="text-muted">Suggested questions:</small>
            <div class="d-flex flex-wrap gap-2 mt-1">
                ${questions.map(q => `
                    <button class="btn btn-outline-primary btn-sm suggestion-btn" 
                            data-question="${q}">
                        ${q}
                    </button>
                `).join('')}
            </div>
        `;
        
        // Add click handlers for suggestion buttons
        suggestionsContainer.querySelectorAll('.suggestion-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const question = e.target.dataset.question;
                this.messageInput.value = question;
                this.handleSendMessage();
                suggestionsContainer.remove(); // Remove suggestions after use
            });
        });
        
        this.chatContainer.appendChild(suggestionsContainer);
        this.scrollToBottom();
    }
    
    async handleSendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isTyping) return;
        
        // Add user message
        this.addMessage('user', message);
        this.messageInput.value = '';
        this.autoResizeTextarea();
        
        // Show typing indicator
        this.showTypingIndicator();
        
        try {
            // Send to RAG-enhanced backend
            const response = await this.sendToRAGBackend(message);
            this.hideTypingIndicator();
            
            if (response.success) {
                this.addMessage('assistant', response.response, {
                    intent: response.intent,
                    hasData: response.has_data
                });
                
                // Add data visualization if available
                if (response.has_data) {
                    this.addDataVisualization(response.intent);
                }
            } else {
                throw new Error('Backend returned error');
            }
            
        } catch (error) {
            console.error('Chat error:', error);
            this.hideTypingIndicator();
            this.addMessage('assistant', 
                this.currentLanguage === 'az' 
                    ? 'Üzr istəyirəm, hazırda bir problem var. Zəhmət olmasa yenidən cəhd edin.'
                    : 'I apologize, but I\'m having trouble right now. Please try again.'
            );
        }
    }
    
    async sendToRAGBackend(message) {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                language: this.currentLanguage
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }
    
    addMessage(sender, content, metadata = {}) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message mb-3`;
        
        const timestamp = new Date().toLocaleTimeString([], {
            hour: '2-digit', 
            minute: '2-digit'
        });
        
        let intentBadge = '';
        if (metadata.intent && sender === 'assistant') {
            const intentLabels = {
                currency_inquiry: '💱',
                location_inquiry: '📍', 
                service_inquiry: '🏛️',
                banking_general: '🏦',
                general_inquiry: '💬'
            };
            intentBadge = `<span class="intent-badge">${intentLabels[metadata.intent] || '💬'}</span>`;
        }
        
        messageDiv.innerHTML = `
            <div class="message-content">
                <div class="message-header">
                    <strong>${sender === 'user' ? 'You' : 'AI Assistant'}</strong>
                    ${intentBadge}
                    <small class="text-muted">${timestamp}</small>
                </div>
                <div class="message-text">${this.formatMessage(content)}</div>
                ${metadata.hasData ? '<small class="text-primary">📊 Using real-time data</small>' : ''}
            </div>
        `;
        
        this.chatContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    addSystemMessage(content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'system-message text-center text-muted small my-2';
        messageDiv.innerHTML = `<em>${content}</em>`;
        this.chatContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    formatMessage(content) {
        // Convert line breaks to HTML
        return content
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')  // Bold
            .replace(/\*(.*?)\*/g, '<em>$1</em>')  // Italic
            .replace(/•/g, '&bull;');  // Bullet points
    }
    
    async addDataVisualization(intent) {
        if (intent === 'currency_inquiry') {
            try {
                const ratesResponse = await fetch('/api/currency/rates');
                const ratesData = await ratesResponse.json();
                
                if (ratesData.success) {
                    this.addCurrencyRatesTable(ratesData.data);
                }
            } catch (error) {
                console.error('Failed to load currency data:', error);
            }
        }
    }
    
    addCurrencyRatesTable(ratesData) {
        if (!ratesData.currencies) return;
        
        const tableDiv = document.createElement('div');
        tableDiv.className = 'currency-rates-table mt-2 mb-3';
        
        const majorCurrencies = ratesData.currencies
            .filter(curr => ['USD', 'EUR', 'RUB', 'TRY', 'GBP'].includes(curr.Code))
            .slice(0, 5);
        
        tableDiv.innerHTML = `
            <div class="card">
                <div class="card-header py-2">
                    <small><strong>💱 Current CBAR Rates (${ratesData.date})</strong></small>
                </div>
                <div class="card-body p-2">
                    <div class="table-responsive">
                        <table class="table table-sm table-striped mb-0">
                            <thead>
                                <tr>
                                    <th>Currency</th>
                                    <th>Rate (AZN)</th>
                                    <th>Change</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${majorCurrencies.map(curr => `
                                    <tr>
                                        <td>
                                            <strong>${curr.Code}</strong>
                                            <br><small class="text-muted">${curr.Nominal}</small>
                                        </td>
                                        <td><strong>${curr.Value}</strong></td>
                                        <td>
                                            <span class="text-success">
                                                <i class="fas fa-arrow-up"></i> 0.01%
                                            </span>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
        
        this.chatContainer.appendChild(tableDiv);
        this.scrollToBottom();
    }
    
    showTypingIndicator() {
        this.isTyping = true;
        this.sendButton.disabled = true;
        
        if (this.typingIndicator) {
            this.typingIndicator.style.display = 'block';
            this.scrollToBottom();
        }
    }
    
    hideTypingIndicator() {
        this.isTyping = false;
        this.sendButton.disabled = false;
        
        if (this.typingIndicator) {
            this.typingIndicator.style.display = 'none';
        }
    }
    
    autoResizeTextarea() {
        if (this.messageInput) {
            this.messageInput.style.height = 'auto';
            this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
        }
    }
    
    scrollToBottom() {
        setTimeout(() => {
            this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
        }, 100);
    }
}

// Initialize chat interface when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('chat-messages')) {
        new RAGChatInterface();
    }
});

// Add some CSS for better styling
const chatStyles = `
<style>
.message {
    animation: fadeIn 0.3s ease-in;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.user-message .message-content {
    background: #007bff;
    color: white;
    border-radius: 15px 15px 5px 15px;
    padding: 10px 15px;
    margin-left: 20%;
}

.assistant-message .message-content {
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 15px 15px 15px 5px;
    padding: 10px 15px;
    margin-right: 20%;
}

.message-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 5px;
    font-size: 0.85em;
}

.intent-badge {
    font-size: 1.1em;
    margin-left: 5px;
}

.suggested-questions {
    margin: 15px 0;
    padding: 15px;
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    border-radius: 10px;
    border-left: 4px solid #007bff;
}

.suggestion-btn {
    transition: all 0.2s ease;
}

.suggestion-btn:hover {
    transform: translateY(-1px);
    box-shadow: 0 2px 5px rgba(0,123,255,0.3);
}

.currency-rates-table {
    animation: slideUp 0.4s ease-out;
}

@keyframes slideUp {
    from { 
        opacity: 0; 
        transform: translateY(20px); 
    }
    to { 
        opacity: 1; 
        transform: translateY(0); 
    }
}

#typing-indicator {
    padding: 10px 15px;
    margin-right: 20%;
    background: #f8f9fa;
    border-radius: 15px 15px 15px 5px;
    border: 1px solid #e9ecef;
}

.typing-dots {
    display: inline-flex;
    align-items: center;
}

.typing-dots span {
    height: 8px;
    width: 8px;
    background: #007bff;
    border-radius: 50%;
    display: inline-block;
    margin: 0 2px;
    animation: typing 1.5s infinite ease-in-out;
}

.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
    0%, 60%, 100% { opacity: 0.3; }
    30% { opacity: 1; }
}

.system-message {
    margin: 10px 20%;
    padding: 8px 15px;
    background: rgba(0,123,255,0.1);
    border-radius: 20px;
    border: 1px solid rgba(0,123,255,0.2);
}
</style>
`;

// Inject styles
document.head.insertAdjacentHTML('beforeend', chatStyles);