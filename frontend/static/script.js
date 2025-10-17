// Chat functionality
const chatContainer = document.getElementById('chatContainer');
const questionInput = document.getElementById('questionInput');
const sendButton = document.getElementById('sendButton');
const quickButtons = document.querySelectorAll('.quick-btn');

// Add message to chat
function addMessage(content, isUser = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = isUser ? '👤' : '🤖';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = content;

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    chatContainer.appendChild(messageDiv);

    // Scroll to bottom
    chatContainer.scrollTop = chatContainer.scrollHeight;

    return messageDiv;
}

// Add loading indicator
function addLoadingIndicator() {
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message bot-message';
    loadingDiv.id = 'loadingMessage';

    loadingDiv.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <div class="loading">
                <div class="loading-dot"></div>
                <div class="loading-dot"></div>
                <div class="loading-dot"></div>
            </div>
        </div>
    `;

    chatContainer.appendChild(loadingDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;

    return loadingDiv;
}

// Remove loading indicator
function removeLoadingIndicator() {
    const loading = document.getElementById('loadingMessage');
    if (loading) {
        loading.remove();
    }
}

// Format sources with clickable URLs
function formatSources(sources) {
    if (!sources || sources.length === 0) {
        return '';
    }

    const uniqueSources = [];
    const seen = new Set();

    sources.forEach(source => {
        const key = `${source.card_name}_${source.card_type}`;
        if (!seen.has(key)) {
            seen.add(key);
            uniqueSources.push(source);
        }
    });

    const sourceItems = uniqueSources.map(source => {
        const badgeClass = source.card_type === 'credit' ? 'badge-credit' : 'badge-debet';
        const badgeText = source.card_type === 'credit' ? 'Kredit' : 'Debet';
        const url = source.url || '#';

        return `
            <div class="source-item">
                <div class="source-name">
                    <span>${source.card_name}</span>
                    <span class="source-badge ${badgeClass}">${badgeText}</span>
                </div>
                <a href="${url}" target="_blank" class="source-link" title="Ətraflı məlumat">
                    <span>Link</span>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                        <polyline points="15 3 21 3 21 9"></polyline>
                        <line x1="10" y1="14" x2="21" y2="3"></line>
                    </svg>
                </a>
            </div>
        `;
    }).join('');

    return `
        <div class="sources">
            <div class="sources-title">📎 Mənbələr (ətraflı məlumat üçün klikləyin):</div>
            ${sourceItems}
        </div>
    `;
}

// Send question
async function sendQuestion() {
    const question = questionInput.value.trim();

    if (!question) {
        return;
    }

    // Add user message
    addMessage(`<p>${question}</p>`, true);
    questionInput.value = '';

    // Disable input
    sendButton.disabled = true;
    questionInput.disabled = true;

    // Add loading indicator
    const loading = addLoadingIndicator();

    try {
        // Send to API
        const response = await fetch('/api/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ question })
        });

        const data = await response.json();

        // Remove loading
        removeLoadingIndicator();

        if (response.ok) {
            // Add bot response
            const sourcesHtml = formatSources(data.sources);
            const content = data.answer + sourcesHtml;
            addMessage(content);
        } else {
            // Show error
            addMessage(`<p>❌ Xəta: ${data.error || 'Naməlum xəta baş verdi'}</p>`);
        }

    } catch (error) {
        console.error('Error:', error);
        removeLoadingIndicator();
        addMessage('<p>❌ Xəta: Server ilə əlaqə qurula bilmədi</p>');
    } finally {
        // Re-enable input
        sendButton.disabled = false;
        questionInput.disabled = false;
        questionInput.focus();
    }
}

// Event listeners
sendButton.addEventListener('click', sendQuestion);

questionInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendQuestion();
    }
});

// Quick question buttons
quickButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        const question = btn.dataset.question;
        questionInput.value = question;
        sendQuestion();
    });
});

// Focus input on load
questionInput.focus();
