-- -- Create the banking_assistant schema
-- CREATE SCHEMA IF NOT EXISTS banking_assistant;

-- -- Set the search path to use our schema
-- SET search_path TO banking_assistant;

-- -- Banks table
-- CREATE TABLE IF NOT EXISTS banks (
--     id SERIAL PRIMARY KEY,
--     bank_code VARCHAR(50) UNIQUE NOT NULL,
--     name VARCHAR(100) NOT NULL,
--     website VARCHAR(200),
--     phone VARCHAR(20),
--     email VARCHAR(100),
--     is_active BOOLEAN DEFAULT true,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

-- -- Loan rates table
-- CREATE TABLE IF NOT EXISTS loan_rates (
--     id SERIAL PRIMARY KEY,
--     bank_id INTEGER REFERENCES banks(id) ON DELETE CASCADE,
--     loan_type VARCHAR(50) NOT NULL, -- 'personal', 'mortgage', 'auto'
--     min_rate DECIMAL(5,2) NOT NULL,
--     max_rate DECIMAL(5,2) NOT NULL,
--     min_amount DECIMAL(12,2) DEFAULT 1000,
--     max_amount DECIMAL(12,2) DEFAULT 1000000,
--     term_months INTEGER DEFAULT 60,
--     currency VARCHAR(3) DEFAULT 'AZN',
--     requirements TEXT,
--     is_active BOOLEAN DEFAULT true,
--     last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

-- -- Bank branches table
-- CREATE TABLE IF NOT EXISTS branches (
--     id SERIAL PRIMARY KEY,
--     bank_id INTEGER REFERENCES banks(id) ON DELETE CASCADE,
--     branch_name VARCHAR(100) NOT NULL,
--     address TEXT NOT NULL,
--     city VARCHAR(50) DEFAULT 'Baku',
--     latitude DECIMAL(10,8),
--     longitude DECIMAL(11,8),
--     phone VARCHAR(20),
--     email VARCHAR(100),
--     working_hours VARCHAR(100) DEFAULT '09:00-18:00',
--     services TEXT[], -- Array of available services
--     is_active BOOLEAN DEFAULT true,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

-- -- Currency rates table (for caching CBAR data)
-- CREATE TABLE IF NOT EXISTS currency_rates (
--     id SERIAL PRIMARY KEY,
--     currency_code VARCHAR(3) NOT NULL,
--     rate_to_azn DECIMAL(10,6) NOT NULL,
--     rate_date DATE NOT NULL DEFAULT CURRENT_DATE,
--     source VARCHAR(50) DEFAULT 'CBAR',
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     UNIQUE(currency_code, rate_date)
-- );

-- -- Chat history table (optional)
-- CREATE TABLE IF NOT EXISTS chat_history (
--     id SERIAL PRIMARY KEY,
--     session_id VARCHAR(100),
--     user_message TEXT NOT NULL,
--     ai_response TEXT NOT NULL,
--     language VARCHAR(5) DEFAULT 'en',
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

-- -- User queries log (for analytics)
-- CREATE TABLE IF NOT EXISTS user_queries (
--     id SERIAL PRIMARY KEY,
--     query_type VARCHAR(50), -- 'loan_comparison', 'branch_finder', 'chat', 'currency'
--     parameters JSONB,
--     response_data JSONB,
--     processing_time_ms INTEGER,
--     user_ip VARCHAR(45),
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

-- -- Insert sample data
-- INSERT INTO banks (bank_code, name, website, phone) VALUES
-- ('PASHA', 'PASHA Bank', 'https://www.pashabank.az', '+994 12 967 00 00'),
-- ('KAPITAL', 'Kapital Bank', 'https://www.kapitalbank.az', '+994 12 496 80 80'),
-- ('IBA', 'International Bank of Azerbaijan', 'https://www.ibar.az', '+994 12 935 00 00'),
-- ('ACCESS', 'AccessBank', 'https://www.accessbank.az', '+994 12 945 00 00'),
-- ('RABITABANK', 'RabiteBank', 'https://www.rabitabank.az', '+994 12 919 19 19')
-- ON CONFLICT (bank_code) DO NOTHING;

-- -- Insert loan rates
-- INSERT INTO loan_rates (bank_id, loan_type, min_rate, max_rate, min_amount, max_amount) VALUES
-- (1, 'personal', 8.5, 12.0, 1000, 50000),
-- (1, 'mortgage', 6.0, 8.5, 10000, 500000),
-- (1, 'auto', 7.5, 10.0, 5000, 100000),
-- (2, 'personal', 9.0, 13.0, 1000, 45000),
-- (2, 'mortgage', 6.5, 9.0, 10000, 450000),
-- (2, 'auto', 8.0, 11.0, 5000, 90000),
-- (3, 'personal', 10.0, 14.0, 1000, 40000),
-- (3, 'mortgage', 7.0, 9.5, 10000, 400000),
-- (3, 'auto', 8.5, 11.5, 5000, 85000),
-- (4, 'personal', 11.0, 15.0, 1000, 35000),
-- (4, 'mortgage', 7.5, 10.0, 10000, 350000),
-- (4, 'auto', 9.0, 12.0, 5000, 80000),
-- (5, 'personal', 9.5, 13.5, 1000, 42000),
-- (5, 'mortgage', 6.8, 8.8, 10000, 480000),
-- (5, 'auto', 8.2, 10.8, 5000, 95000);

-- -- Insert branch data
-- INSERT INTO branches (bank_id, branch_name, address, latitude, longitude, phone, working_hours) VALUES
-- (1, 'PASHA Tower Main Branch', '153 Heydar Aliyev prospekti, Baku', 40.3777, 49.8531, '+994 12 967 00 00', '09:00-18:00'),
-- (1, 'Nizami Branch', 'Nizami küçəsi 67, Baku', 40.4093, 49.8671, '+994 12 967 00 01', '09:00-17:00'),
-- (2, 'Main Branch', '28 May küçəsi 1, Baku', 40.3656, 49.8348, '+994 12 496 80 80', '09:00-18:00'),
-- (2, 'Elmlar Branch', 'Elmlar prospekti 25, Baku', 40.3950, 49.8520, '+994 12 496 80 81', '09:00-17:00'),
-- (3, 'Central Branch', '67 Nizami küçəsi, Baku', 40.4037, 49.8682, '+994 12 935 00 00', '09:00-18:00'),
-- (4, 'Port Baku Branch', '153 Neftchilar prospekti, Baku', 40.3587, 49.8263, '+994 12 945 00 00', '09:00-18:00'),
-- (5, 'Yasamal Branch', 'Ahmad Rajabli küçəsi 2, Baku', 40.3947, 49.8206, '+994 12 919 19 19', '09:00-18:00');

-- -- Insert current currency rates
-- INSERT INTO currency_rates (currency_code, rate_to_azn) VALUES
-- ('USD', 1.70),
-- ('EUR', 1.85),
-- ('RUB', 0.019),
-- ('TRY', 0.050),
-- ('GBP', 2.10),
-- ('RUR', 0.019)
-- ON CONFLICT (currency_code, rate_date) DO UPDATE SET 
--     rate_to_azn = EXCLUDED.rate_to_azn,
--     created_at = CURRENT_TIMESTAMP;

-- -- Create indexes for better performance
-- CREATE INDEX IF NOT EXISTS idx_loan_rates_bank_type ON loan_rates(bank_id, loan_type);
-- CREATE INDEX IF NOT EXISTS idx_branches_bank_location ON branches(bank_id, latitude, longitude);
-- CREATE INDEX IF NOT EXISTS idx_currency_rates_code_date ON currency_rates(currency_code, rate_date);
-- CREATE INDEX IF NOT EXISTS idx_chat_history_session ON chat_history(session_id, created_at);

-- -- Create a view for easy loan comparison
-- CREATE OR REPLACE VIEW loan_comparison_view AS
-- SELECT 
--     b.name as bank_name,
--     b.phone as bank_phone,
--     b.website as bank_website,
--     lr.loan_type,
--     lr.min_rate,
--     lr.max_rate,
--     lr.min_amount,
--     lr.max_amount,
--     lr.term_months,
--     lr.currency
-- FROM banks b
-- JOIN loan_rates lr ON b.id = lr.bank_id
-- WHERE b.is_active = true AND lr.is_active = true
-- ORDER BY lr.loan_type, lr.min_rate;

-- -- Grant permissions (if needed)
--  GRANT ALL PRIVILEGES ON SCHEMA banking_assistant TO tg_db_owner;
--  GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA banking_assistant TO tg_db_owner;
--  GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA banking_assistant TO tg_db_owner;

-- AI Banking Assistant - Enhanced Database Schema
-- Version 2.0.0 with Security, Performance, and Analytics Improvements

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create the banking_assistant schema
CREATE SCHEMA IF NOT EXISTS banking_assistant;

-- Set the search path to use our schema
SET search_path TO banking_assistant;

-- =============================================================================
-- AUDIT AND SECURITY TABLES
-- =============================================================================

-- Audit log for all table changes
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    table_name VARCHAR(63) NOT NULL,
    operation VARCHAR(10) NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
    old_values JSONB,
    new_values JSONB,
    user_id UUID,
    user_ip INET,
    user_agent TEXT,
    session_id VARCHAR(100),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT audit_log_operation_check CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE'))
);

-- Create index for audit log queries
CREATE INDEX idx_audit_log_table_timestamp ON audit_log(table_name, timestamp);
CREATE INDEX idx_audit_log_user_timestamp ON audit_log(user_id, timestamp);

-- Security events table
CREATE TABLE security_events (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'INFO' CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    description TEXT NOT NULL,
    user_id UUID,
    ip_address INET,
    user_agent TEXT,
    session_id VARCHAR(100),
    additional_data JSONB,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    resolved_by UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_security_events_type_created ON security_events(event_type, created_at);
CREATE INDEX idx_security_events_severity_unresolved ON security_events(severity, resolved) WHERE NOT resolved;

-- =============================================================================
-- ENHANCED BANKS TABLE
-- =============================================================================

CREATE TABLE banks (
    id SERIAL PRIMARY KEY,
    bank_code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    name_az VARCHAR(100), -- Azerbaijani name
    full_name VARCHAR(200),
    website VARCHAR(200),
    phone VARCHAR(20),
    email VARCHAR(100),
    
    -- Additional bank information
    swift_code VARCHAR(11),
    bank_license VARCHAR(50),
    establishment_date DATE,
    headquarters_address TEXT,
    total_assets DECIMAL(15,2),
    employee_count INTEGER,
    
    -- API configuration
    api_base_url VARCHAR(200),
    api_version VARCHAR(20),
    api_key_encrypted TEXT, -- Encrypted API key
    api_rate_limit INTEGER DEFAULT 100,
    api_timeout INTEGER DEFAULT 30,
    
    -- Status and metadata
    is_active BOOLEAN DEFAULT true,
    is_featured BOOLEAN DEFAULT false,
    display_order INTEGER DEFAULT 999,
    logo_url VARCHAR(200),
    primary_color VARCHAR(7), -- Hex color code
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_api_check TIMESTAMP,
    
    -- Search optimization
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', coalesce(name, '') || ' ' || coalesce(name_az, '') || ' ' || coalesce(full_name, ''))
    ) STORED
);

-- Indexes for banks table
CREATE INDEX idx_banks_active_featured ON banks(is_active, is_featured);
CREATE INDEX idx_banks_display_order ON banks(display_order, name);
CREATE INDEX idx_banks_search_vector ON banks USING GIN(search_vector);
CREATE INDEX idx_banks_updated_at ON banks(updated_at);

-- =============================================================================
-- ENHANCED LOAN RATES TABLE
-- =============================================================================

CREATE TABLE loan_rates (
    id BIGSERIAL PRIMARY KEY,
    bank_id INTEGER REFERENCES banks(id) ON DELETE CASCADE,
    
    -- Loan product details
    loan_type VARCHAR(50) NOT NULL CHECK (loan_type IN ('personal', 'mortgage', 'auto', 'business', 'student', 'secured')),
    product_name VARCHAR(100),
    product_code VARCHAR(50),
    
    -- Rate information
    min_rate DECIMAL(5,2) NOT NULL CHECK (min_rate >= 0 AND min_rate <= 100),
    max_rate DECIMAL(5,2) NOT NULL CHECK (max_rate >= min_rate AND max_rate <= 100),
    promotional_rate DECIMAL(5,2) CHECK (promotional_rate >= 0 AND promotional_rate <= 100),
    promotional_period_months INTEGER,
    
    -- Amount and term limits
    min_amount DECIMAL(12,2) DEFAULT 1000 CHECK (min_amount > 0),
    max_amount DECIMAL(12,2) DEFAULT 1000000 CHECK (max_amount >= min_amount),
    min_term_months INTEGER DEFAULT 12 CHECK (min_term_months > 0),
    max_term_months INTEGER DEFAULT 360 CHECK (max_term_months >= min_term_months),
    
    -- Currency and fees
    currency VARCHAR(3) DEFAULT 'AZN' CHECK (currency IN ('AZN', 'USD', 'EUR')),
    processing_fee DECIMAL(10,2) DEFAULT 0,
    processing_fee_percentage DECIMAL(5,2) DEFAULT 0,
    early_repayment_fee DECIMAL(5,2) DEFAULT 0,
    insurance_required BOOLEAN DEFAULT FALSE,
    insurance_rate DECIMAL(5,2) DEFAULT 0,
    
    -- Eligibility and requirements
    min_age INTEGER DEFAULT 18,
    max_age INTEGER DEFAULT 70,
    min_income DECIMAL(10,2),
    employment_required BOOLEAN DEFAULT TRUE,
    collateral_required BOOLEAN DEFAULT FALSE,
    guarantor_required BOOLEAN DEFAULT FALSE,
    
    -- Additional terms
    requirements TEXT,
    benefits TEXT,
    terms_and_conditions TEXT,
    
    -- Status and tracking
    is_active BOOLEAN DEFAULT true,
    is_featured BOOLEAN DEFAULT FALSE,
    application_url VARCHAR(200),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    effective_from DATE DEFAULT CURRENT_DATE,
    effective_until DATE,
    
    -- Performance tracking
    application_count INTEGER DEFAULT 0,
    approval_rate DECIMAL(5,2),
    average_processing_days INTEGER,
    
    -- Data source tracking
    data_source VARCHAR(50) DEFAULT 'manual',
    source_url VARCHAR(200),
    last_scraped TIMESTAMP,
    
    CONSTRAINT loan_rates_date_check CHECK (effective_until IS NULL OR effective_until > effective_from)
);

-- Indexes for loan_rates table
CREATE INDEX idx_loan_rates_bank_type_active ON loan_rates(bank_id, loan_type, is_active);
CREATE INDEX idx_loan_rates_type_currency_effective ON loan_rates(loan_type, currency, effective_from, effective_until);
CREATE INDEX idx_loan_rates_amount_range ON loan_rates(min_amount, max_amount);
CREATE INDEX idx_loan_rates_rate_range ON loan_rates(min_rate, max_rate);
CREATE INDEX idx_loan_rates_featured_active ON loan_rates(is_featured, is_active) WHERE is_featured AND is_active;

-- =============================================================================
-- ENHANCED BRANCHES TABLE
-- =============================================================================

CREATE TABLE branches (
    id BIGSERIAL PRIMARY KEY,
    bank_id INTEGER REFERENCES banks(id) ON DELETE CASCADE,
    
    -- Branch identification
    branch_code VARCHAR(50),
    branch_name VARCHAR(100) NOT NULL,
    branch_type VARCHAR(50) DEFAULT 'full_service' CHECK (branch_type IN ('full_service', 'sub_branch', 'atm', 'kiosk', 'mobile')),
    
    -- Location information
    address TEXT NOT NULL,
    city VARCHAR(50) DEFAULT 'Baku',
    district VARCHAR(50),
    postal_code VARCHAR(10),
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    
    -- Contact information
    phone VARCHAR(20),
    email VARCHAR(100),
    manager_name VARCHAR(100),
    
    -- Operating information
    working_hours VARCHAR(100) DEFAULT '09:00-18:00',
    working_days VARCHAR(50) DEFAULT 'Mon-Fri',
    saturday_hours VARCHAR(100),
    is_24_7 BOOLEAN DEFAULT FALSE,
    
    -- Services and amenities
    services TEXT[], -- Array of available services
    languages TEXT[] DEFAULT '{az,en}', -- Supported languages
    accessibility_features TEXT[],
    parking_available BOOLEAN DEFAULT FALSE,
    wifi_available BOOLEAN DEFAULT FALSE,
    atm_available BOOLEAN DEFAULT TRUE,
    
    -- Status and metadata
    is_active BOOLEAN DEFAULT true,
    is_flagship BOOLEAN DEFAULT FALSE,
    opening_date DATE,
    renovation_date DATE,
    
    -- Performance metrics
    customer_rating DECIMAL(3,2) CHECK (customer_rating >= 0 AND customer_rating <= 5),
    review_count INTEGER DEFAULT 0,
    wait_time_minutes INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_verified TIMESTAMP,
    
    -- Search optimization
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', coalesce(branch_name, '') || ' ' || coalesce(address, '') || ' ' || coalesce(city, '') || ' ' || coalesce(district, ''))
    ) STORED,
    
    CONSTRAINT branches_coordinates_check CHECK (
        (latitude IS NULL AND longitude IS NULL) OR 
        (latitude IS NOT NULL AND longitude IS NOT NULL AND 
         latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180)
    )
);

-- Indexes for branches table
CREATE INDEX idx_branches_bank_active ON branches(bank_id, is_active);
CREATE INDEX idx_branches_location ON branches(latitude, longitude) WHERE latitude IS NOT NULL;
CREATE INDEX idx_branches_city_type ON branches(city, branch_type, is_active);
CREATE INDEX idx_branches_search_vector ON branches USING GIN(search_vector);
CREATE INDEX idx_branches_services ON branches USING GIN(services);

-- =============================================================================
-- ENHANCED CURRENCY RATES TABLE
-- =============================================================================

CREATE TABLE currency_rates (
    id BIGSERIAL PRIMARY KEY,
    currency_code VARCHAR(3) NOT NULL CHECK (length(currency_code) = 3),
    currency_name VARCHAR(50),
    
    -- Rate information
    rate_to_azn DECIMAL(12,6) NOT NULL CHECK (rate_to_azn > 0),
    buy_rate DECIMAL(12,6),
    sell_rate DECIMAL(12,6),
    
    -- Metadata
    rate_date DATE NOT NULL DEFAULT CURRENT_DATE,
    source VARCHAR(50) DEFAULT 'CBAR',
    source_url VARCHAR(200),
    
    -- Change tracking
    previous_rate DECIMAL(12,6),
    change_amount DECIMAL(12,6),
    change_percentage DECIMAL(5,2),
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(currency_code, rate_date, source)
);

-- Indexes for currency_rates table
CREATE INDEX idx_currency_rates_code_date ON currency_rates(currency_code, rate_date DESC);
CREATE INDEX idx_currency_rates_date_active ON currency_rates(rate_date DESC, is_active);
CREATE INDEX idx_currency_rates_source_date ON currency_rates(source, rate_date DESC);

-- =============================================================================
-- USER MANAGEMENT AND SESSIONS
-- =============================================================================

-- Users table (for future authentication features)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(20),
    username VARCHAR(50) UNIQUE,
    
    -- Password and security
    password_hash TEXT, -- For future auth implementation
    password_salt TEXT,
    password_reset_token TEXT,
    password_reset_expires TIMESTAMP,
    
    -- Profile information
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    date_of_birth DATE,
    gender VARCHAR(10) CHECK (gender IN ('male', 'female', 'other', 'prefer_not_to_say')),
    
    -- Preferences
    preferred_language VARCHAR(5) DEFAULT 'en' CHECK (preferred_language IN ('en', 'az')),
    preferred_currency VARCHAR(3) DEFAULT 'AZN',
    notification_preferences JSONB DEFAULT '{}',
    
    -- Location
    city VARCHAR(50),
    country VARCHAR(50) DEFAULT 'Azerbaijan',
    timezone VARCHAR(50) DEFAULT 'Asia/Baku',
    
    -- Status and verification
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    email_verified BOOLEAN DEFAULT FALSE,
    phone_verified BOOLEAN DEFAULT FALSE,
    verification_token TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    last_activity TIMESTAMP
);

-- Indexes for users table
CREATE INDEX idx_users_email_active ON users(email, is_active);
CREATE INDEX idx_users_phone_verified ON users(phone, phone_verified);
CREATE INDEX idx_users_created_at ON users(created_at);
CREATE INDEX idx_users_last_activity ON users(last_activity);

-- Sessions table for tracking user sessions
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_token TEXT UNIQUE NOT NULL,
    
    -- Session metadata
    ip_address INET,
    user_agent TEXT,
    device_type VARCHAR(50),
    browser VARCHAR(50),
    os VARCHAR(50),
    
    -- Geographic information
    country VARCHAR(50),
    city VARCHAR(50),
    timezone VARCHAR(50),
    
    -- Session tracking
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Security
    logout_reason VARCHAR(50), -- 'manual', 'timeout', 'security', 'admin'
    
    CONSTRAINT sessions_expires_check CHECK (expires_at > created_at)
);

-- Indexes for sessions table
CREATE INDEX idx_sessions_user_active ON user_sessions(user_id, is_active);
CREATE INDEX idx_sessions_token ON user_sessions(session_token);
CREATE INDEX idx_sessions_expires ON user_sessions(expires_at);
CREATE INDEX idx_sessions_ip_activity ON user_sessions(ip_address, last_activity);

-- =============================================================================
-- ENHANCED CHAT AND AI TABLES
-- =============================================================================

-- Chat conversations
CREATE TABLE chat_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    session_id VARCHAR(100),
    
    -- Conversation metadata
    title VARCHAR(200),
    language VARCHAR(5) DEFAULT 'en',
    topic VARCHAR(50), -- 'loans', 'branches', 'currency', 'general'
    
    -- AI model information
    ai_model VARCHAR(50) DEFAULT 'gemini-pro',
    model_version VARCHAR(20),
    
    -- Geographic context
    user_location POINT,
    user_timezone VARCHAR(50),
    
    -- Status and tracking
    message_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    satisfaction_rating INTEGER CHECK (satisfaction_rating BETWEEN 1 AND 5),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chat messages
CREATE TABLE chat_messages (
    id BIGSERIAL PRIMARY KEY,
    conversation_id UUID REFERENCES chat_conversations(id) ON DELETE CASCADE,
    
    -- Message content
    message_type VARCHAR(20) NOT NULL CHECK (message_type IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    content_hash TEXT, -- For duplicate detection
    
    -- AI processing information
    tokens_used INTEGER,
    processing_time_ms INTEGER,
    confidence_score DECIMAL(3,2),
    intent_detected VARCHAR(50),
    entities_extracted JSONB,
    
    -- MCP tool usage
    tools_used TEXT[],
    tool_responses JSONB,
    real_time_data_used BOOLEAN DEFAULT FALSE,
    
    -- User feedback
    helpful BOOLEAN,
    user_rating INTEGER CHECK (user_rating BETWEEN 1 AND 5),
    feedback_text TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Message metadata
    user_agent TEXT,
    ip_address INET
);

-- Indexes for chat tables
CREATE INDEX idx_chat_conversations_user_active ON chat_conversations(user_id, is_active);
CREATE INDEX idx_chat_conversations_session ON chat_conversations(session_id);
CREATE INDEX idx_chat_conversations_created ON chat_conversations(created_at DESC);
CREATE INDEX idx_chat_messages_conversation_created ON chat_messages(conversation_id, created_at);
CREATE INDEX idx_chat_messages_type_created ON chat_messages(message_type, created_at);
CREATE INDEX idx_chat_messages_tools ON chat_messages USING GIN(tools_used);

-- =============================================================================
-- ANALYTICS AND USAGE TRACKING
-- =============================================================================

-- User queries log for analytics
CREATE TABLE user_queries (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    session_id VARCHAR(100),
    
    -- Query information
    query_type VARCHAR(50) NOT NULL, -- 'loan_comparison', 'branch_finder', 'chat', 'currency'
    endpoint VARCHAR(100),
    http_method VARCHAR(10),
    
    -- Request details
    parameters JSONB,
    user_agent TEXT,
    ip_address INET,
    referer TEXT,
    
    -- Geographic and device info
    country VARCHAR(50),
    city VARCHAR(50),
    device_type VARCHAR(50),
    browser VARCHAR(50),
    os VARCHAR(50),
    
    -- Response details
    response_data JSONB,
    response_status INTEGER,
    processing_time_ms INTEGER,
    data_source VARCHAR(50), -- 'mcp', 'database', 'cache'
    
    -- Error tracking
    error_message TEXT,
    error_code VARCHAR(50),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Analytics aggregation table
CREATE TABLE daily_analytics (
    date DATE PRIMARY KEY,
    
    -- Usage metrics
    total_requests INTEGER DEFAULT 0,
    unique_users INTEGER DEFAULT 0,
    unique_sessions INTEGER DEFAULT 0,
    
    -- Query type breakdown
    loan_queries INTEGER DEFAULT 0,
    branch_queries INTEGER DEFAULT 0,
    chat_queries INTEGER DEFAULT 0,
    currency_queries INTEGER DEFAULT 0,
    
    -- Performance metrics
    avg_response_time_ms DECIMAL(8,2),
    error_rate DECIMAL(5,2),
    
    -- Geographic breakdown
    users_by_country JSONB DEFAULT '{}',
    users_by_city JSONB DEFAULT '{}',
    
    -- Device breakdown
    desktop_users INTEGER DEFAULT 0,
    mobile_users INTEGER DEFAULT 0,
    tablet_users INTEGER DEFAULT 0,
    
    -- Data source breakdown
    mcp_requests INTEGER DEFAULT 0,
    database_requests INTEGER DEFAULT 0,
    cache_requests INTEGER DEFAULT 0,
    
    -- Language breakdown
    english_users INTEGER DEFAULT 0,
    azerbaijani_users INTEGER DEFAULT 0,
    
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for analytics tables
CREATE INDEX idx_user_queries_type_created ON user_queries(query_type, created_at);
CREATE INDEX idx_user_queries_user_created ON user_queries(user_id, created_at);
CREATE INDEX idx_user_queries_session_created ON user_queries(session_id, created_at);
CREATE INDEX idx_user_queries_ip_created ON user_queries(ip_address, created_at);
CREATE INDEX idx_user_queries_status_created ON user_queries(response_status, created_at);

-- =============================================================================
-- NOTIFICATIONS AND ALERTS
-- =============================================================================

-- System notifications
CREATE TABLE notifications (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- Notification details
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    notification_type VARCHAR(50) NOT NULL, -- 'rate_alert', 'system', 'promotional', 'security'
    priority VARCHAR(20) DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    
    -- Delivery channels
    channels TEXT[] DEFAULT '{web}', -- 'web', 'email', 'sms', 'push'
    
    -- Status
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    delivered BOOLEAN DEFAULT FALSE,
    delivery_attempts INTEGER DEFAULT 0,
    
    -- Metadata
    action_url VARCHAR(200),
    action_text VARCHAR(50),
    expires_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    scheduled_for TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Rate alerts (for future feature)
CREATE TABLE rate_alerts (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- Alert criteria
    alert_type VARCHAR(20) NOT NULL CHECK (alert_type IN ('loan_rate', 'currency_rate')),
    currency_code VARCHAR(3),
    loan_type VARCHAR(50),
    bank_id INTEGER REFERENCES banks(id) ON DELETE CASCADE,
    
    -- Thresholds
    target_rate DECIMAL(10,6),
    condition VARCHAR(10) CHECK (condition IN ('above', 'below', 'equals')),
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    triggered_count INTEGER DEFAULT 0,
    last_triggered TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

-- Indexes for notifications
CREATE INDEX idx_notifications_user_unread ON notifications(user_id, is_read) WHERE NOT is_read;
CREATE INDEX idx_notifications_type_created ON notifications(notification_type, created_at);
CREATE INDEX idx_rate_alerts_user_active ON rate_alerts(user_id, is_active);

-- =============================================================================
-- SYSTEM CONFIGURATION AND SETTINGS
-- =============================================================================

-- Application settings
CREATE TABLE app_settings (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT,
    value_type VARCHAR(20) DEFAULT 'string' CHECK (value_type IN ('string', 'integer', 'decimal', 'boolean', 'json')),
    description TEXT,
    category VARCHAR(50),
    is_public BOOLEAN DEFAULT FALSE,
    updated_by UUID REFERENCES users(id),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Feature flags
CREATE TABLE feature_flags (
    name VARCHAR(100) PRIMARY KEY,
    enabled BOOLEAN DEFAULT FALSE,
    description TEXT,
    rollout_percentage DECIMAL(5,2) DEFAULT 100 CHECK (rollout_percentage BETWEEN 0 AND 100),
    target_users UUID[],
    target_groups TEXT[],
    environment VARCHAR(20) DEFAULT 'all',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- VIEWS FOR EASY QUERYING
-- =============================================================================

-- Enhanced loan comparison view
CREATE OR REPLACE VIEW loan_comparison_view AS
SELECT 
    b.id as bank_id,
    b.name as bank_name,
    b.name_az as bank_name_az,
    b.phone as bank_phone,
    b.website as bank_website,
    b.logo_url,
    b.primary_color,
    b.is_featured as bank_featured,
    lr.id as rate_id,
    lr.loan_type,
    lr.product_name,
    lr.min_rate,
    lr.max_rate,
    lr.promotional_rate,
    lr.min_amount,
    lr.max_amount,
    lr.min_term_months,
    lr.max_term_months,
    lr.currency,
    lr.processing_fee,
    lr.processing_fee_percentage,
    lr.requirements,
    lr.benefits,
    lr.application_url,
    lr.is_featured as product_featured,
    lr.approval_rate,
    lr.average_processing_days,
    lr.last_updated
FROM banks b
JOIN loan_rates lr ON b.id = lr.bank_id
WHERE b.is_active = true AND lr.is_active = true
    AND (lr.effective_until IS NULL OR lr.effective_until > CURRENT_DATE)
ORDER BY lr.loan_type, lr.min_rate, b.display_order;

-- Branch finder view with enhanced information
CREATE OR REPLACE VIEW branch_finder_view AS
SELECT 
    b.id as bank_id,
    b.name as bank_name,
    b.name_az as bank_name_az,
    b.logo_url,
    b.primary_color,
    br.id as branch_id,
    br.branch_name,
    br.branch_type,
    br.address,
    br.city,
    br.district,
    br.latitude,
    br.longitude,
    br.phone,
    br.email,
    br.working_hours,
    br.working_days,
    br.saturday_hours,
    br.is_24_7,
    br.services,
    br.languages,
    br.accessibility_features,
    br.parking_available,
    br.wifi_available,
    br.atm_available,
    br.customer_rating,
    br.review_count,
    br.wait_time_minutes,
    br.is_flagship
FROM banks b
JOIN branches br ON b.id = br.bank_id
WHERE b.is_active = true AND br.is_active = true
ORDER BY b.display_order, br.branch_name;

-- Current currency rates view
CREATE OR REPLACE VIEW current_currency_rates AS
SELECT DISTINCT ON (currency_code)
    currency_code,
    currency_name,
    rate_to_azn,
    buy_rate,
    sell_rate,
    rate_date,
    source,
    change_amount,
    change_percentage,
    created_at
FROM currency_rates
WHERE is_active = true
ORDER BY currency_code, rate_date DESC, created_at DESC;

-- Analytics summary view
CREATE OR REPLACE VIEW analytics_summary AS
SELECT 
    DATE_TRUNC('day', created_at) as date,
    COUNT(*) as total_queries,
    COUNT(DISTINCT COALESCE(user_id, session_id)) as unique_users,
    COUNT(*) FILTER (WHERE query_type = 'loan_comparison') as loan_queries,
    COUNT(*) FILTER (WHERE query_type = 'branch_finder') as branch_queries,
    COUNT(*) FILTER (WHERE query_type = 'chat') as chat_queries,
    COUNT(*) FILTER (WHERE query_type = 'currency') as currency_queries,
    AVG(processing_time_ms) as avg_response_time,
    COUNT(*) FILTER (WHERE response_status >= 400) * 100.0 / COUNT(*) as error_rate
FROM user_queries
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', created_at)
ORDER BY date DESC;

-- =============================================================================
-- FUNCTIONS AND TRIGGERS
-- =============================================================================

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at columns
CREATE TRIGGER update_banks_updated_at BEFORE UPDATE ON banks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_branches_updated_at BEFORE UPDATE ON branches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_chat_conversations_updated_at BEFORE UPDATE ON chat_conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to create audit log entries
CREATE OR REPLACE FUNCTION create_audit_log()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (
        table_name,
        operation,
        old_values,
        new_values,
        timestamp
    ) VALUES (
        TG_TABLE_NAME,
        TG_OP,
        CASE WHEN TG_OP = 'DELETE' THEN row_to_json(OLD) ELSE NULL END,
        CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN row_to_json(NEW) ELSE NULL END,
        CURRENT_TIMESTAMP
    );
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Audit triggers (add selectively to important tables)
CREATE TRIGGER audit_banks AFTER INSERT OR UPDATE OR DELETE ON banks
    FOR EACH ROW EXECUTE FUNCTION create_audit_log();

CREATE TRIGGER audit_loan_rates AFTER INSERT OR UPDATE OR DELETE ON loan_rates
    FOR EACH ROW EXECUTE FUNCTION create_audit_log();

-- Function to clean old data
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS void AS $$
BEGIN
    -- Clean old audit logs (keep 1 year)
    DELETE FROM audit_log WHERE timestamp < CURRENT_DATE - INTERVAL '1 year';
    
    -- Clean old user queries (keep 6 months)
    DELETE FROM user_queries WHERE created_at < CURRENT_DATE - INTERVAL '6 months';
    
    -- Clean expired sessions
    DELETE FROM user_sessions WHERE expires_at < CURRENT_TIMESTAMP;
    
    -- Clean old notifications (keep 3 months)
    DELETE FROM notifications WHERE created_at < CURRENT_DATE - INTERVAL '3 months';
    
    -- Clean old security events (keep 1 year)
    DELETE FROM security_events WHERE created_at < CURRENT_DATE - INTERVAL '1 year';
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- SAMPLE DATA INSERTION
-- =============================================================================

-- Insert enhanced bank data
INSERT INTO banks (bank_code, name, name_az, full_name, website, phone, swift_code, establishment_date, logo_url, primary_color, display_order) VALUES
('PASHA', 'PASHA Bank', 'PAŞA Bank', 'PASHA Bank OJSC', 'https://www.pashabank.az', '+994 12 967 00 00', 'PASHAZ22', '2007-01-01', '/static/images/banks/pasha.png', '#1f4e79', 1),
('KAPITAL', 'Kapital Bank', 'Kapital Bank', 'Kapital Bank OJSC', 'https://www.kapitalbank.az', '+994 12 496 80 80', 'AIIBAZ2X', '1992-01-01', '/static/images/banks/kapital.png', '#27ae60', 2),
('IBA', 'International Bank of Azerbaijan', 'Azərbaycan Beynəlxalq Bankı', 'International Bank of Azerbaijan CJSC', 'https://www.ibar.az', '+994 12 935 00 00', 'IBAZAZ22', '1992-01-01', '/static/images/banks/iba.png', '#e74c3c', 3),
('ACCESS', 'AccessBank', 'AccessBank', 'AccessBank OJSC', 'https://www.accessbank.az', '+994 12 945 00 00', 'ABAZAZ22', '2002-01-01', '/static/images/banks/access.png', '#3498db', 4),
('RABITABANK', 'RabiteBank', 'RabitəBank', 'RabiteBank OJSC', 'https://www.rabitabank.az', '+994 12 919 19 19', 'RBAZAZ22', '1993-01-01', '/static/images/banks/rabite.png', '#f39c12', 5)
ON CONFLICT (bank_code) DO UPDATE SET
    name = EXCLUDED.name,
    name_az = EXCLUDED.name_az,
    full_name = EXCLUDED.full_name,
    website = EXCLUDED.website,
    phone = EXCLUDED.phone,
    swift_code = EXCLUDED.swift_code,
    establishment_date = EXCLUDED.establishment_date,
    logo_url = EXCLUDED.logo_url,
    primary_color = EXCLUDED.primary_color,
    display_order = EXCLUDED.display_order,
    updated_at = CURRENT_TIMESTAMP;

-- Insert enhanced loan rates with more details
INSERT INTO loan_rates (bank_id, loan_type, product_name, min_rate, max_rate, min_amount, max_amount, min_term_months, max_term_months, currency, processing_fee, benefits, requirements) VALUES
-- PASHA Bank
(1, 'personal', 'Personal Loan Standard', 8.5, 12.0, 1000, 50000, 12, 72, 'AZN', 50, 'Quick approval, No collateral required', 'Minimum age 18, Regular income, Employment verification'),
(1, 'mortgage', 'Home Loan', 6.0, 8.5, 10000, 500000, 60, 360, 'AZN', 0, 'Competitive rates, Flexible terms', 'Property appraisal, Income verification, Insurance required'),
(1, 'auto', 'Car Loan', 7.5, 10.0, 5000, 100000, 12, 84, 'AZN', 100, 'Quick processing, New and used cars', 'Valid drivers license, Insurance required'),

-- Kapital Bank
(2, 'personal', 'Express Personal Loan', 9.0, 13.0, 1000, 45000, 12, 60, 'AZN', 25, 'Fast approval, Online application', 'Age 21-65, Minimum salary 300 AZN'),
(2, 'mortgage', 'Dream Home Mortgage', 6.5, 9.0, 10000, 450000, 60, 300, 'AZN', 0, 'Low down payment, Flexible repayment', 'Stable employment, Property evaluation'),
(2, 'auto', 'Auto Finance', 8.0, 11.0, 5000, 90000, 12, 72, 'AZN', 75, 'Comprehensive coverage, Extended warranty', 'Age 23+, Valid license'),

-- International Bank
(3, 'personal', 'Consumer Loan', 10.0, 14.0, 1000, 40000, 12, 60, 'AZN', 30, 'Established bank, Trusted service', 'Employment history, Credit check'),
(3, 'mortgage', 'Property Loan', 7.0, 9.5, 10000, 400000, 60, 240, 'AZN', 0, 'Experienced lending, Property advisory', 'Down payment 20%, Property insurance'),
(3, 'auto', 'Vehicle Financing', 8.5, 11.5, 5000, 85000, 12, 72, 'AZN', 80, 'Wide dealer network, Quick approval', 'Clean driving record, Full coverage insurance'),

-- AccessBank
(4, 'personal', 'Quick Cash Loan', 11.0, 15.0, 1000, 35000, 6, 48, 'AZN', 40, 'Minimal documentation, Same day approval', 'Government ID, Proof of income'),
(4, 'mortgage', 'Home Purchase Loan', 7.5, 10.0, 10000, 350000, 60, 300, 'AZN', 0, 'First-time buyer programs, Guidance', 'Credit score check, Property valuation'),
(4, 'auto', 'Car Purchase Loan', 9.0, 12.0, 5000, 80000, 12, 60, 'AZN', 60, 'Used car financing, Flexible terms', 'Vehicle inspection, Comprehensive insurance'),

-- RabiteBank  
(5, 'personal', 'Personal Finance', 9.5, 13.5, 1000, 42000, 12, 72, 'AZN', 35, 'Customer-focused service, Competitive rates', 'Steady income, Age 20-70'),
(5, 'mortgage', 'Housing Loan', 6.8, 8.8, 10000, 480000, 60, 360, 'AZN', 0, 'Longest terms available, Low rates', 'Property documents, Income certification'),
(5, 'auto', 'Vehicle Loan', 8.2, 10.8, 5000, 95000, 12, 84, 'AZN', 50, 'New and used vehicles, Extended terms', 'Vehicle registration, Insurance coverage')
ON CONFLICT DO NOTHING;

-- Insert enhanced branch data with more details
INSERT INTO branches (bank_id, branch_code, branch_name, branch_type, address, city, latitude, longitude, phone, working_hours, services, languages, parking_available, atm_available) VALUES
-- PASHA Bank branches
(1, 'PASHA001', 'PASHA Tower Main Branch', 'full_service', '153 Heydar Aliyev prospekti, Baku', 'Baku', 40.3777, 49.8531, '+994 12 967 00 00', '09:00-18:00', '{personal_banking,business_banking,currency_exchange,loans,deposits,cards,insurance}', '{az,en,ru}', true, true),
(1, 'PASHA002', 'Nizami Branch', 'full_service', 'Nizami küçəsi 67, Baku', 'Baku', 40.4093, 49.8671, '+994 12 967 00 01', '09:00-17:00', '{personal_banking,currency_exchange,loans,deposits,cards}', '{az,en}', false, true),

-- Kapital Bank branches
(2, 'KAP001', 'Main Branch', 'full_service', '28 May küçəsi 1, Baku', 'Baku', 40.3656, 49.8348, '+994 12 496 80 80', '09:00-18:00', '{personal_banking,business_banking,currency_exchange,loans,deposits,cards,mobile_banking}', '{az,en,ru}', true, true),
(2, 'KAP002', 'Elmlar Branch', 'sub_branch', 'Elmlar prospekti 25, Baku', 'Baku', 40.3950, 49.8520, '+994 12 496 80 81', '09:00-17:00', '{personal_banking,currency_exchange,deposits,cards}', '{az,en}', true, true),

-- International Bank branches
(3, 'IBA001', 'Central Branch', 'full_service', '67 Nizami küçəsi, Baku', 'Baku', 40.4037, 49.8682, '+994 12 935 00 00', '09:00-18:00', '{personal_banking,business_banking,currency_exchange,loans,deposits,cards,trade_finance}', '{az,en,ru}', false, true),

-- AccessBank branches
(4, 'ACC001', 'Port Baku Branch', 'full_service', '153 Neftchilar prospekti, Baku', 'Baku', 40.3587, 49.8263, '+994 12 945 00 00', '09:00-18:00', '{personal_banking,business_banking,currency_exchange,loans,deposits,cards}', '{az,en}', true, true),

-- RabiteBank branches
(5, 'RAB001', 'Yasamal Branch', 'full_service', 'Ahmad Rajabli küçəsi 2, Baku', 'Baku', 40.3947, 49.8206, '+994 12 919 19 19', '09:00-18:00', '{personal_banking,business_banking,currency_exchange,loans,deposits,cards}', '{az,en}', true, true)
ON CONFLICT DO NOTHING;

-- Insert current currency rates
INSERT INTO currency_rates (currency_code, currency_name, rate_to_azn, buy_rate, sell_rate, source) VALUES
('USD', 'US Dollar', 1.7000, 1.6950, 1.7050, 'CBAR'),
('EUR', 'Euro', 1.8500, 1.8450, 1.8550, 'CBAR'),
('RUB', 'Russian Ruble', 0.0190, 0.0189, 0.0191, 'CBAR'),
('TRY', 'Turkish Lira', 0.0500, 0.0499, 0.0501, 'CBAR'),
('GBP', 'British Pound', 2.1000, 2.0950, 2.1050, 'CBAR')
ON CONFLICT (currency_code, rate_date, source) DO UPDATE SET 
    rate_to_azn = EXCLUDED.rate_to_azn,
    buy_rate = EXCLUDED.buy_rate,
    sell_rate = EXCLUDED.sell_rate,
    created_at = CURRENT_TIMESTAMP;

-- Insert application settings
INSERT INTO app_settings (key, value, value_type, description, category, is_public) VALUES
('app_name', 'AI Banking Assistant', 'string', 'Application name', 'general', true),
('app_version', '2.0.0', 'string', 'Application version', 'general', true),
('default_language', 'en', 'string', 'Default application language', 'localization', true),
('supported_languages', '["en", "az"]', 'json', 'Supported languages', 'localization', true),
('default_currency', 'AZN', 'string', 'Default currency', 'financial', true),
('max_loan_amount', '1000000', 'integer', 'Maximum loan amount', 'financial', true),
('min_loan_amount', '1000', 'integer', 'Minimum loan amount', 'financial', true),
('currency_update_interval', '3600', 'integer', 'Currency update interval in seconds', 'system', false),
('enable_analytics', 'true', 'boolean', 'Enable analytics tracking', 'system', false),
('maintenance_mode', 'false', 'boolean', 'Maintenance mode status', 'system', false)
ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    updated_at = CURRENT_TIMESTAMP;

-- Insert feature flags
INSERT INTO feature_flags (name, enabled, description, environment) VALUES
('mcp_integration', true, 'Enable MCP real-time data integration', 'all'),
('ai_chat', true, 'Enable AI chat functionality', 'all'),
('voice_input', true, 'Enable voice input in chat', 'all'),
('pwa_features', true, 'Enable Progressive Web App features', 'all'),
('rate_alerts', false, 'Enable rate alert notifications', 'development'),
('advanced_analytics', true, 'Enable advanced analytics tracking', 'all'),
('social_auth', false, 'Enable social media authentication', 'development'),
('dark_mode', true, 'Enable dark mode theme', 'all')
ON CONFLICT (name) DO UPDATE SET
    enabled = EXCLUDED.enabled,
    description = EXCLUDED.description,
    updated_at = CURRENT_TIMESTAMP;

-- =============================================================================
-- CREATE INDEXES FOR PERFORMANCE
-- =============================================================================

-- Performance indexes for common queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_queries_performance 
    ON user_queries(query_type, created_at DESC, processing_time_ms);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_messages_performance 
    ON chat_messages(conversation_id, created_at DESC, message_type);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_loan_rates_search 
    ON loan_rates(loan_type, currency, is_active, min_rate) 
    WHERE is_active = true;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_branches_geographic 
    ON branches(latitude, longitude, city, is_active) 
    WHERE is_active = true AND latitude IS NOT NULL;

-- =============================================================================
-- GRANT PERMISSIONS
-- =============================================================================

-- Grant permissions to application user
GRANT USAGE ON SCHEMA banking_assistant TO banking_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA banking_assistant TO banking_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA banking_assistant TO banking_user;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA banking_assistant TO banking_user;

-- Create read-only user for analytics
-- CREATE USER analytics_user WITH PASSWORD 'analytics_password';
-- GRANT USAGE ON SCHEMA banking_assistant TO analytics_user;
-- GRANT SELECT ON ALL TABLES IN SCHEMA banking_assistant TO analytics_user;

-- =============================================================================
-- FINAL SETUP
-- =============================================================================

-- Refresh materialized views if any exist
-- REFRESH MATERIALIZED VIEW IF EXISTS loan_rates_summary;

-- Update table statistics
ANALYZE;

-- Create a cleanup job (to be scheduled with pg_cron or external scheduler)
-- SELECT cron.schedule('cleanup-old-data', '0 2 * * *', 'SELECT banking_assistant.cleanup_old_data();');

COMMENT ON SCHEMA banking_assistant IS 'AI Banking Assistant - Enhanced schema v2.0.0 with security, performance, and analytics improvements';

-- =============================================================================
-- COMPLETION MESSAGE
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE 'AI Banking Assistant database schema v2.0.0 created successfully!';
    RAISE NOTICE 'Features included:';
    RAISE NOTICE '- Enhanced security with audit logs and user management';
    RAISE NOTICE '- Advanced analytics and usage tracking';
    RAISE NOTICE '- Chat system with AI conversation management';
    RAISE NOTICE '- Notification system and rate alerts';
    RAISE NOTICE '- Performance optimizations and comprehensive indexing';
    RAISE NOTICE '- Sample data for immediate testing';
    RAISE NOTICE '- Ready for production deployment';
END $$;