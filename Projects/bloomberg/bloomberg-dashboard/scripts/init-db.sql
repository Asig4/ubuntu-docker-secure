-- ============================================================
-- Bloomberg Dashboard — Initialisation PostgreSQL
-- ============================================================
-- Ce script est exécuté automatiquement au premier démarrage
-- via docker-entrypoint-initdb.d

-- Watchlists dynamiques
CREATE TABLE IF NOT EXISTS watchlists (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    assets JSONB NOT NULL DEFAULT '[]',
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, name)
);

-- Configuration des layouts par utilisateur
CREATE TABLE IF NOT EXISTS user_layouts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    layout_name VARCHAR(100) NOT NULL,
    panels_config JSONB NOT NULL DEFAULT '{}',
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, layout_name)
);

-- Règles d'alertes custom
CREATE TABLE IF NOT EXISTS alert_rules (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    asset VARCHAR(50) NOT NULL,
    condition VARCHAR(20) NOT NULL CHECK (condition IN ('above', 'below', 'pct_change_above', 'pct_change_below', 'volume_spike')),
    threshold DECIMAL NOT NULL,
    timeframe VARCHAR(10) DEFAULT '1h',
    channel VARCHAR(20) NOT NULL CHECK (channel IN ('telegram', 'email', 'webhook', 'all')),
    webhook_url TEXT,
    active BOOLEAN DEFAULT true,
    last_triggered_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Utilisateurs de l'API
CREATE TABLE IF NOT EXISTS api_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    role VARCHAR(20) DEFAULT 'viewer' CHECK (role IN ('admin', 'editor', 'viewer')),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE
);

-- Index pour les performances
CREATE INDEX IF NOT EXISTS idx_watchlists_user_id ON watchlists(user_id);
CREATE INDEX IF NOT EXISTS idx_alert_rules_user_id ON alert_rules(user_id);
CREATE INDEX IF NOT EXISTS idx_alert_rules_asset ON alert_rules(asset);
CREATE INDEX IF NOT EXISTS idx_alert_rules_active ON alert_rules(active) WHERE active = true;

-- Fonction trigger pour updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers auto-update
CREATE TRIGGER update_watchlists_updated_at
    BEFORE UPDATE ON watchlists
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_layouts_updated_at
    BEFORE UPDATE ON user_layouts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_alert_rules_updated_at
    BEFORE UPDATE ON alert_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Données initiales: watchlist par défaut
INSERT INTO watchlists (user_id, name, assets, is_default) VALUES
(1, 'Crypto Majeurs', '["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT", "AVAX/USDT", "DOT/USDT", "MATIC/USDT", "LINK/USDT"]', true),
(1, 'Indices & Forex', '["^GSPC", "^IXIC", "^FCHI", "^GDAXI", "EURUSD=X", "GBPUSD=X", "GC=F", "CL=F"]', false)
ON CONFLICT DO NOTHING;

-- Message de confirmation
DO $$
BEGIN
    RAISE NOTICE 'Bloomberg Dashboard — Base de données initialisée avec succès';
END
$$;
