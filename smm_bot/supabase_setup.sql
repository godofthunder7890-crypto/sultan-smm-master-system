-- SULTAN SMM MASTER SYSTEM — Supabase Database Setup
-- Run this in your Supabase SQL editor ONCE before starting the bot.

-- Users table
CREATE TABLE IF NOT EXISTS users (
    telegram_id BIGINT PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    balance DECIMAL(12,2) DEFAULT 0.00,
    total_spent DECIMAL(12,2) DEFAULT 0.00,
    total_orders INT DEFAULT 0,
    is_banned BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(telegram_id),
    provider TEXT NOT NULL,
    provider_order_id TEXT,
    service_id TEXT NOT NULL,
    service_name TEXT,
    link TEXT NOT NULL,
    quantity INT NOT NULL,
    charge DECIMAL(12,2) NOT NULL,
    status TEXT DEFAULT 'Pending',
    start_count INT,
    remains INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Services table
CREATE TABLE IF NOT EXISTS services (
    id SERIAL PRIMARY KEY,
    provider TEXT NOT NULL,
    service_id TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT,
    rate DECIMAL(12,4) NOT NULL,
    min_order INT,
    max_order INT,
    description TEXT,
    last_synced TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(provider, service_id)
);

-- Transactions / Wallet table
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(telegram_id),
    type TEXT NOT NULL,       -- 'credit' or 'debit'
    amount DECIMAL(12,2) NOT NULL,
    transaction_id TEXT,      -- UPI transaction ID
    status TEXT DEFAULT 'Pending',   -- Pending / Completed / Rejected
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Provider balances log
CREATE TABLE IF NOT EXISTS provider_balances (
    id SERIAL PRIMARY KEY,
    provider TEXT NOT NULL,
    balance DECIMAL(12,2),
    currency TEXT DEFAULT 'USD',
    checked_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_provider ON orders(provider);
CREATE INDEX IF NOT EXISTS idx_services_provider ON services(provider);
CREATE INDEX IF NOT EXISTS idx_services_category ON services(category);
CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);

-- RLS Policies (enable Row Level Security via Supabase Dashboard or run below)
-- For service_role key (used in bot), RLS is bypassed automatically.
-- If using anon key, add policies here.

SELECT 'Sultan SMM Database setup complete! 🏛️' AS message;
