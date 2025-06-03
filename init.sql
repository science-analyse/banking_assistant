-- Initialize banking AI database
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255),
    user_message TEXT,
    ai_response TEXT,
    sentiment JSONB,
    entities JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_analyses (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255),
    document_type VARCHAR(100),
    analysis_result JSONB,
    confidence FLOAT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_conversations_session ON conversations(session_id);
CREATE INDEX idx_conversations_timestamp ON conversations(timestamp);
CREATE INDEX idx_documents_type ON document_analyses(document_type);
