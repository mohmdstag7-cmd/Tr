-- supabase/schema.sql — PostgreSQL schema for MT5 Trading Workstation
-- Supabase: uuid, timestamptz, jsonb, user_id FK, RLS enabled (policies in rls.sql)

-- Enable pgcrypto for gen_random_uuid()
create extension if not exists "pgcrypto";

-- Helper: updated_at trigger
create or replace function mt5tw_set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

-- accounts
create table if not exists public.accounts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  login bigint not null unique,
  server text not null,
  name text,
  currency text,
  balance double precision default 0,
  equity double precision default 0,
  leverage int,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_accounts_updated_at before update on public.accounts for each row execute function mt5tw_set_updated_at();

-- sessions
create table if not exists public.sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  account_id uuid not null references public.accounts(id) on delete cascade,
  started_at timestamptz not null,
  ended_at timestamptz,
  status text not null default 'active',
  terminal_info jsonb default '{}'::jsonb,
  created_at timestamptz not null default now()
);

-- strategy_configs
create table if not exists public.strategy_configs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null,
  version text not null default '1.0.0',
  params jsonb not null default '{}'::jsonb,
  description text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_strategy_configs_updated_at before update on public.strategy_configs for each row execute function mt5tw_set_updated_at();

-- signals
create table if not exists public.signals (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  time timestamptz not null,
  symbol text not null,
  strategy text not null,
  strategy_config_id uuid references public.strategy_configs(id) on delete set null,
  direction text not null check (direction in ('buy','sell')),
  price double precision not null,
  sl double precision,
  tp double precision,
  confidence double precision,
  meta jsonb default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_signals_time_symbol_strategy on public.signals(time, symbol, strategy);

-- decision_traces
create table if not exists public.decision_traces (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  signal_id uuid not null references public.signals(id) on delete cascade,
  decision text not null check (decision in ('accept','reject','filter')),
  reason text,
  risk_check text,
  trace jsonb default '{}'::jsonb,
  created_at timestamptz not null default now()
);

-- trades
create table if not exists public.trades (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  ticket bigint unique,
  symbol text not null,
  mode text not null check (mode in ('live','demo','backtest')),
  side text not null check (side in ('buy','sell')),
  volume double precision not null,
  open_price double precision,
  close_price double precision,
  sl double precision,
  tp double precision,
  open_time timestamptz,
  close_time timestamptz,
  profit double precision default 0,
  swap double precision default 0,
  commission double precision default 0,
  strategy text,
  strategy_config_id uuid references public.strategy_configs(id) on delete set null,
  signal_id uuid references public.signals(id) on delete set null,
  status text not null default 'open' check (status in ('open','closed','pending','canceled')),
  magic bigint,
  comment text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_trades_updated_at before update on public.trades for each row execute function mt5tw_set_updated_at();
create index if not exists idx_trades_open_close_symbol_mode on public.trades(open_time, close_time, symbol, mode);

-- trade_events
create table if not exists public.trade_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  trade_id uuid not null references public.trades(id) on delete cascade,
  event_type text not null,
  price double precision,
  volume double precision,
  time timestamptz not null,
  meta jsonb default '{}'::jsonb
);

-- mt5_requests
create table if not exists public.mt5_requests (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  method text not null,
  params jsonb default '{}'::jsonb,
  response jsonb,
  duration_ms int,
  status text not null default 'ok',
  error text,
  created_at timestamptz not null default now()
);
create index if not exists idx_mt5_requests_created_at on public.mt5_requests(created_at);

-- account_snapshots
create table if not exists public.account_snapshots (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  account_id uuid not null references public.accounts(id) on delete cascade,
  time timestamptz not null,
  balance double precision not null,
  equity double precision not null,
  margin double precision,
  free_margin double precision,
  margin_level double precision,
  profit double precision default 0,
  created_at timestamptz not null default now()
);
create index if not exists idx_account_snapshots_time on public.account_snapshots(time);

-- risk_events
create table if not exists public.risk_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  time timestamptz not null,
  account_id uuid references public.accounts(id) on delete set null,
  type text not null,
  severity text not null check (severity in ('info','warning','critical')),
  message text not null,
  meta jsonb default '{}'::jsonb,
  created_at timestamptz not null default now()
);

-- model_versions
create table if not exists public.model_versions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null,
  version text not null,
  path text,
  metrics jsonb default '{}'::jsonb,
  stage text default 'dev',
  created_at timestamptz not null default now(),
  unique(name, version)
);

-- backtest_runs
create table if not exists public.backtest_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  strategy_config_id uuid references public.strategy_configs(id) on delete set null,
  model_version_id uuid references public.model_versions(id) on delete set null,
  started_at timestamptz not null,
  ended_at timestamptz,
  params jsonb default '{}'::jsonb,
  results jsonb default '{}'::jsonb,
  status text not null default 'running' check (status in ('running','completed','failed')),
  created_at timestamptz not null default now()
);

-- journal
create table if not exists public.journal (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  time timestamptz not null,
  title text not null,
  content text,
  tags jsonb default '[]'::jsonb,
  trade_id uuid references public.trades(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_journal_updated_at before update on public.journal for each row execute function mt5tw_set_updated_at();

-- audit_log
create table if not exists public.audit_log (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete set null,
  time timestamptz not null,
  "user" text,
  action text not null,
  entity text not null,
  entity_id uuid,
  details jsonb default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_audit_log_time on public.audit_log(time);

-- app_logs
create table if not exists public.app_logs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete set null,
  time timestamptz not null,
  level text not null check (level in ('DEBUG','INFO','WARNING','ERROR','CRITICAL')),
  category text not null,
  message text not null,
  meta jsonb default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_app_logs_time_category_level on public.app_logs(time, category, level);

-- health_checks
create table if not exists public.health_checks (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete set null,
  time timestamptz not null,
  component text not null,
  status text not null check (status in ('ok','degraded','down')),
  latency_ms int,
  details jsonb default '{}'::jsonb,
  created_at timestamptz not null default now()
);

-- performance_metrics
create table if not exists public.performance_metrics (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  time timestamptz not null,
  metric text not null,
  value double precision not null,
  bucket text,
  meta jsonb default '{}'::jsonb,
  created_at timestamptz not null default now()
);

-- daily_reports
create table if not exists public.daily_reports (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  date date not null unique,
  content text,
  metrics jsonb default '{}'::jsonb,
  created_at timestamptz not null default now()
);

-- calendar_events
create table if not exists public.calendar_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete set null,
  time timestamptz not null,
  title text not null,
  importance text check (importance in ('low','medium','high')),
  currency text,
  forecast text,
  previous text,
  actual text,
  meta jsonb default '{}'::jsonb,
  created_at timestamptz not null default now()
);

-- outbox (server-side mirror for idempotency / debugging; local SQLite is source of truth)
create table if not exists public.outbox (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete set null,
  table_name text not null,
  record_id uuid not null,
  operation text not null check (operation in ('insert','update','delete','upsert')),
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  synced_at timestamptz,
  attempts int not null default 0,
  last_error text,
  status text not null default 'pending' check (status in ('pending','synced','failed'))
);
