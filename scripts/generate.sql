-- Create the banking_assistant schema
CREATE SCHEMA IF NOT EXISTS banking_assistant;

-- Set the search path to use our schema
SET search_path TO banking_assistant;

-- Banks table
CREATE TABLE IF NOT EXISTS banks (
    id SERIAL PRIMARY KEY,
    bank_code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    website VARCHAR(200),
    phone VARCHAR(20),
    email VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Loan rates table
CREATE TABLE IF NOT EXISTS loan_rates (
    id SERIAL PRIMARY KEY,
    bank_id INTEGER REFERENCES banks(id) ON DELETE CASCADE,
    loan_type VARCHAR(50) NOT NULL, -- 'personal', 'mortgage', 'auto'
    min_rate DECIMAL(5,2) NOT NULL,
    max_rate DECIMAL(5,2) NOT NULL,
    min_amount DECIMAL(12,2) DEFAULT 1000,
    max_amount DECIMAL(12,2) DEFAULT 1000000,
    term_months INTEGER DEFAULT 60,
    currency VARCHAR(3) DEFAULT 'AZN',
    requirements TEXT,
    is_active BOOLEAN DEFAULT true,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bank branches table
CREATE TABLE IF NOT EXISTS branches (
    id SERIAL PRIMARY KEY,
    bank_id INTEGER REFERENCES banks(id) ON DELETE CASCADE,
    branch_name VARCHAR(100) NOT NULL,
    address TEXT NOT NULL,
    city VARCHAR(50) DEFAULT 'Baku',
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    phone VARCHAR(20),
    email VARCHAR(100),
    working_hours VARCHAR(100) DEFAULT '09:00-18:00',
    services TEXT[], -- Array of available services
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Currency rates table (for caching CBAR data)
CREATE TABLE IF NOT EXISTS currency_rates (
    id SERIAL PRIMARY KEY,
    currency_code VARCHAR(3) NOT NULL,
    rate_to_azn DECIMAL(10,6) NOT NULL,
    rate_date DATE NOT NULL DEFAULT CURRENT_DATE,
    source VARCHAR(50) DEFAULT 'CBAR',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(currency_code, rate_date)
);

-- Chat history table (optional)
CREATE TABLE IF NOT EXISTS chat_history (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100),
    user_message TEXT NOT NULL,
    ai_response TEXT NOT NULL,
    language VARCHAR(5) DEFAULT 'en',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User queries log (for analytics)
CREATE TABLE IF NOT EXISTS user_queries (
    id SERIAL PRIMARY KEY,
    query_type VARCHAR(50), -- 'loan_comparison', 'branch_finder', 'chat', 'currency'
    parameters JSONB,
    response_data JSONB,
    processing_time_ms INTEGER,
    user_ip VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample data
INSERT INTO banks (bank_code, name, website, phone) VALUES
('PASHA', 'PASHA Bank', 'https://www.pashabank.az', '+994 12 967 00 00'),
('KAPITAL', 'Kapital Bank', 'https://www.kapitalbank.az', '+994 12 496 80 80'),
('IBA', 'International Bank of Azerbaijan', 'https://www.ibar.az', '+994 12 935 00 00'),
('ACCESS', 'AccessBank', 'https://www.accessbank.az', '+994 12 945 00 00'),
('RABITABANK', 'RabiteBank', 'https://www.rabitabank.az', '+994 12 919 19 19')
ON CONFLICT (bank_code) DO NOTHING;

-- Insert loan rates
INSERT INTO loan_rates (bank_id, loan_type, min_rate, max_rate, min_amount, max_amount) VALUES
(1, 'personal', 8.5, 12.0, 1000, 50000),
(1, 'mortgage', 6.0, 8.5, 10000, 500000),
(1, 'auto', 7.5, 10.0, 5000, 100000),
(2, 'personal', 9.0, 13.0, 1000, 45000),
(2, 'mortgage', 6.5, 9.0, 10000, 450000),
(2, 'auto', 8.0, 11.0, 5000, 90000),
(3, 'personal', 10.0, 14.0, 1000, 40000),
(3, 'mortgage', 7.0, 9.5, 10000, 400000),
(3, 'auto', 8.5, 11.5, 5000, 85000),
(4, 'personal', 11.0, 15.0, 1000, 35000),
(4, 'mortgage', 7.5, 10.0, 10000, 350000),
(4, 'auto', 9.0, 12.0, 5000, 80000),
(5, 'personal', 9.5, 13.5, 1000, 42000),
(5, 'mortgage', 6.8, 8.8, 10000, 480000),
(5, 'auto', 8.2, 10.8, 5000, 95000);

-- Insert branch data
INSERT INTO branches (bank_id, branch_name, address, latitude, longitude, phone, working_hours) VALUES
(1, 'PASHA Tower Main Branch', '153 Heydar Aliyev prospekti, Baku', 40.3777, 49.8531, '+994 12 967 00 00', '09:00-18:00'),
(1, 'Nizami Branch', 'Nizami küçəsi 67, Baku', 40.4093, 49.8671, '+994 12 967 00 01', '09:00-17:00'),
(2, 'Main Branch', '28 May küçəsi 1, Baku', 40.3656, 49.8348, '+994 12 496 80 80', '09:00-18:00'),
(2, 'Elmlar Branch', 'Elmlar prospekti 25, Baku', 40.3950, 49.8520, '+994 12 496 80 81', '09:00-17:00'),
(3, 'Central Branch', '67 Nizami küçəsi, Baku', 40.4037, 49.8682, '+994 12 935 00 00', '09:00-18:00'),
(4, 'Port Baku Branch', '153 Neftchilar prospekti, Baku', 40.3587, 49.8263, '+994 12 945 00 00', '09:00-18:00'),
(5, 'Yasamal Branch', 'Ahmad Rajabli küçəsi 2, Baku', 40.3947, 49.8206, '+994 12 919 19 19', '09:00-18:00');

-- Insert current currency rates
INSERT INTO currency_rates (currency_code, rate_to_azn) VALUES
('USD', 1.70),
('EUR', 1.85),
('RUB', 0.019),
('TRY', 0.050),
('GBP', 2.10),
('RUR', 0.019)
ON CONFLICT (currency_code, rate_date) DO UPDATE SET 
    rate_to_azn = EXCLUDED.rate_to_azn,
    created_at = CURRENT_TIMESTAMP;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_loan_rates_bank_type ON loan_rates(bank_id, loan_type);
CREATE INDEX IF NOT EXISTS idx_branches_bank_location ON branches(bank_id, latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_currency_rates_code_date ON currency_rates(currency_code, rate_date);
CREATE INDEX IF NOT EXISTS idx_chat_history_session ON chat_history(session_id, created_at);

-- Create a view for easy loan comparison
CREATE OR REPLACE VIEW loan_comparison_view AS
SELECT 
    b.name as bank_name,
    b.phone as bank_phone,
    b.website as bank_website,
    lr.loan_type,
    lr.min_rate,
    lr.max_rate,
    lr.min_amount,
    lr.max_amount,
    lr.term_months,
    lr.currency
FROM banks b
JOIN loan_rates lr ON b.id = lr.bank_id
WHERE b.is_active = true AND lr.is_active = true
ORDER BY lr.loan_type, lr.min_rate;

-- Grant permissions (if needed)
 GRANT ALL PRIVILEGES ON SCHEMA banking_assistant TO tg_db_owner;
 GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA banking_assistant TO tg_db_owner;
 GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA banking_assistant TO tg_db_owner;