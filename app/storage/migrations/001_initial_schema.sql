-- 001_initial_schema.sql — Initial schema for MT5 Trading Workstation (SQLite)
-- Forward-only migration. All tables from SPEC Part E2.

PRAGMA foreign_keys=ON;

-- _migrations tracking (also created in database.py, kept idempotent)
CREATE TABLE IF NOT EXISTS _migrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT UNIQUE NOT NULL,
    applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- accounts
CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    login INTEGER NOT NULL UNIQUE,
    server TEXT NOT NULL,
    name TEXT,
    currency TEXT,
    balance REAL DEFAULT 0,
    equity REAL DEFAULT 0,
    leverage INTEGER,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- sessions
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    terminal_info TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- strategy_configs
CREATE TABLE IF NOT EXISTS strategy_configs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT '1.0.0',
    params TEXT NOT NULL DEFAULT '{}',
    description TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- signals
CREATE TABLE IF NOT EXISTS signals (
    id TEXT PRIMARY KEY,
    time TEXT NOT NULL,
    symbol TEXT NOT NULL,
    strategy TEXT NOT NULL,
    strategy_config_id TEXT REFERENCES strategy_configs(id) ON DELETE SET NULL,
    direction TEXT NOT NULL CHECK (direction IN ('buy','sell')),
    price REAL NOT NULL,
    sl REAL,
    tp REAL,
    confidence REAL,
    meta TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- decision_traces
CREATE TABLE IF NOT EXISTS decision_traces (
    id TEXT PRIMARY KEY,
    signal_id TEXT NOT NULL REFERENCES signals(id) ON DELETE CASCADE,
    decision TEXT NOT NULL CHECK (decision IN ('accept','reject','filter')),
    reason TEXT,
    risk_check TEXT,
    trace TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- trades
CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    ticket INTEGER UNIQUE,
    symbol TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('live','demo','backtest')),
    side TEXT NOT NULL CHECK (side IN ('buy','sell')),
    volume REAL NOT NULL,
    open_price REAL,
    close_price REAL,
    sl REAL,
    tp REAL,
    open_time TEXT,
    close_time TEXT,
    profit REAL DEFAULT 0,
    swap REAL DEFAULT 0,
    commission REAL DEFAULT 0,
    strategy TEXT,
    strategy_config_id TEXT REFERENCES strategy_configs(id) ON DELETE SET NULL,
    signal_id TEXT REFERENCES signals(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','closed','pending','canceled')),
    magic INTEGER,
    comment TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- trade_events
CREATE TABLE IF NOT EXISTS trade_events (
    id TEXT PRIMARY KEY,
    trade_id TEXT NOT NULL REFERENCES trades(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    price REAL,
    volume REAL,
    time TEXT NOT NULL,
    meta TEXT DEFAULT '{}'
);

-- mt5_requests
CREATE TABLE IF NOT EXISTS mt5_requests (
    id TEXT PRIMARY KEY,
    method TEXT NOT NULL,
    params TEXT DEFAULT '{}',
    response TEXT,
    duration_ms INTEGER,
    status TEXT NOT NULL DEFAULT 'ok',
    error TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- account_snapshots
CREATE TABLE IF NOT EXISTS account_snapshots (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    time TEXT NOT NULL,
    balance REAL NOT NULL,
    equity REAL NOT NULL,
    margin REAL,
    free_margin REAL,
    margin_level REAL,
    profit REAL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- risk_events
CREATE TABLE IF NOT EXISTS risk_events (
    id TEXT PRIMARY KEY,
    time TEXT NOT NULL,
    account_id TEXT REFERENCES accounts(id) ON DELETE SET NULL,
    type TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('info','warning','critical')),
    message TEXT NOT NULL,
    meta TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- model_versions
CREATE TABLE IF NOT EXISTS model_versions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    path TEXT,
    metrics TEXT DEFAULT '{}',
    stage TEXT DEFAULT 'dev',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE(name, version)
);

-- backtest_runs
CREATE TABLE IF NOT EXISTS backtest_runs (
    id TEXT PRIMARY KEY,
    strategy_config_id TEXT REFERENCES strategy_configs(id) ON DELETE SET NULL,
    model_version_id TEXT REFERENCES model_versions(id) ON DELETE SET NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    params TEXT DEFAULT '{}',
    results TEXT DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running','completed','failed')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- journal
CREATE TABLE IF NOT EXISTS journal (
    id TEXT PRIMARY KEY,
    time TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    tags TEXT DEFAULT '[]',
    trade_id TEXT REFERENCES trades(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- audit_log
CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    time TEXT NOT NULL,
    user TEXT,
    action TEXT NOT NULL,
    entity TEXT NOT NULL,
    entity_id TEXT,
    details TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- app_logs
CREATE TABLE IF NOT EXISTS app_logs (
    id TEXT PRIMARY KEY,
    time TEXT NOT NULL,
    level TEXT NOT NULL CHECK (level IN ('DEBUG','INFO','WARNING','ERROR','CRITICAL')),
    category TEXT NOT NULL,
    message TEXT NOT NULL,
    meta TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- health_checks
CREATE TABLE IF NOT EXISTS health_checks (
    id TEXT PRIMARY KEY,
    time TEXT NOT NULL,
    component TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ok','degraded','down')),
    latency_ms INTEGER,
    details TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- performance_metrics
CREATE TABLE IF NOT EXISTS performance_metrics (
    id TEXT PRIMARY KEY,
    time TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    bucket TEXT,
    meta TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- daily_reports
CREATE TABLE IF NOT EXISTS daily_reports (
    id TEXT PRIMARY KEY,
    date TEXT NOT NULL UNIQUE,
    content TEXT,
    metrics TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- calendar_events
CREATE TABLE IF NOT EXISTS calendar_events (
    id TEXT PRIMARY KEY,
    time TEXT NOT NULL,
    title TEXT NOT NULL,
    importance TEXT CHECK (importance IN ('low','medium','high')),
    currency TEXT,
    forecast TEXT,
    previous TEXT,
    actual TEXT,
    meta TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- outbox (local source of truth for Supabase sync)
CREATE TABLE IF NOT EXISTS outbox (
    id TEXT PRIMARY KEY,
    table_name TEXT NOT NULL,
    record_id TEXT NOT NULL,
    operation TEXT NOT NULL CHECK (operation IN ('insert','update','delete','upsert')),
    payload TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    synced_at TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','synced','failed'))
);

-- Indexes per SPEC
CREATE INDEX IF NOT EXISTS idx_signals_time ON signals(time);
CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol);
CREATE INDEX IF NOT EXISTS idx_signals_strategy ON signals(strategy);
CREATE INDEX IF NOT EXISTS idx_signals_time_symbol_strategy ON signals(time, symbol, strategy);

CREATE INDEX IF NOT EXISTS idx_trades_open_time ON trades(open_time);
CREATE INDEX IF NOT EXISTS idx_trades_close_time ON trades(close_time);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_mode ON trades(mode);
CREATE INDEX IF NOT EXISTS idx_trades_open_close_symbol_mode ON trades(open_time, close_time, symbol, mode);

CREATE INDEX IF NOT EXISTS idx_account_snapshots_time ON account_snapshots(time);
CREATE INDEX IF NOT EXISTS idx_mt5_requests_created_at ON mt5_requests(created_at);
CREATE INDEX IF NOT EXISTS idx_app_logs_time ON app_logs(time);
CREATE INDEX IF NOT EXISTS idx_app_logs_category ON app_logs(category);
CREATE INDEX IF NOT EXISTS idx_app_logs_level ON app_logs(level);
CREATE INDEX IF NOT EXISTS idx_app_logs_time_category_level ON app_logs(time, category, level);
CREATE INDEX IF NOT EXISTS idx_audit_log_time ON audit_log(time);

CREATE INDEX IF NOT EXISTS idx_outbox_status ON outbox(status);
CREATE INDEX IF NOT EXISTS idx_outbox_table_record ON outbox(table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_trade_events_trade_id ON trade_events(trade_id);
CREATE INDEX IF NOT EXISTS idx_decision_traces_signal_id ON decision_traces(signal_id);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_time ON performance_metrics(time);
CREATE INDEX IF NOT EXISTS idx_health_checks_time ON health_checks(time);
