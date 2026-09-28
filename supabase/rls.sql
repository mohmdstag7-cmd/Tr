-- supabase/rls.sql — Row Level Security policies (one per table, user_id = auth.uid())

-- Helper: enable RLS on all tables
alter table public.accounts enable row level security;
alter table public.sessions enable row level security;
alter table public.strategy_configs enable row level security;
alter table public.signals enable row level security;
alter table public.decision_traces enable row level security;
alter table public.trades enable row level security;
alter table public.trade_events enable row level security;
alter table public.mt5_requests enable row level security;
alter table public.account_snapshots enable row level security;
alter table public.risk_events enable row level security;
alter table public.model_versions enable row level security;
alter table public.backtest_runs enable row level security;
alter table public.journal enable row level security;
alter table public.audit_log enable row level security;
alter table public.app_logs enable row level security;
alter table public.health_checks enable row level security;
alter table public.performance_metrics enable row level security;
alter table public.daily_reports enable row level security;
alter table public.calendar_events enable row level security;
alter table public.outbox enable row level security;

-- Generic policy template: authenticated users can only access their own rows
-- For tables with user_id column

drop policy if exists "Users manage own accounts" on public.accounts;
create policy "Users manage own accounts" on public.accounts for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "Users manage own sessions" on public.sessions;
create policy "Users manage own sessions" on public.sessions for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "Users manage own strategy_configs" on public.strategy_configs;
create policy "Users manage own strategy_configs" on public.strategy_configs for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "Users manage own signals" on public.signals;
create policy "Users manage own signals" on public.signals for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "Users manage own decision_traces" on public.decision_traces;
create policy "Users manage own decision_traces" on public.decision_traces for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "Users manage own trades" on public.trades;
create policy "Users manage own trades" on public.trades for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "Users manage own trade_events" on public.trade_events;
create policy "Users manage own trade_events" on public.trade_events for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "Users manage own mt5_requests" on public.mt5_requests;
create policy "Users manage own mt5_requests" on public.mt5_requests for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "Users manage own account_snapshots" on public.account_snapshots;
create policy "Users manage own account_snapshots" on public.account_snapshots for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "Users manage own risk_events" on public.risk_events;
create policy "Users manage own risk_events" on public.risk_events for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "Users manage own model_versions" on public.model_versions;
create policy "Users manage own model_versions" on public.model_versions for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "Users manage own backtest_runs" on public.backtest_runs;
create policy "Users manage own backtest_runs" on public.backtest_runs for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "Users manage own journal" on public.journal;
create policy "Users manage own journal" on public.journal for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- audit_log / app_logs / health_checks / calendar_events allow read own + service_role bypass
drop policy if exists "Users manage own audit_log" on public.audit_log;
create policy "Users manage own audit_log" on public.audit_log for all using (auth.uid() = user_id or user_id is null) with check (auth.uid() = user_id);

drop policy if exists "Users manage own app_logs" on public.app_logs;
create policy "Users manage own app_logs" on public.app_logs for all using (auth.uid() = user_id or user_id is null) with check (auth.uid() = user_id);

drop policy if exists "Users manage own health_checks" on public.health_checks;
create policy "Users manage own health_checks" on public.health_checks for all using (auth.uid() = user_id or user_id is null) with check (auth.uid() = user_id);

drop policy if exists "Users manage own performance_metrics" on public.performance_metrics;
create policy "Users manage own performance_metrics" on public.performance_metrics for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "Users manage own daily_reports" on public.daily_reports;
create policy "Users manage own daily_reports" on public.daily_reports for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "Users manage own calendar_events" on public.calendar_events;
create policy "Users manage own calendar_events" on public.calendar_events for all using (auth.uid() = user_id or user_id is null) with check (auth.uid() = user_id);

drop policy if exists "Users manage own outbox" on public.outbox;
create policy "Users manage own outbox" on public.outbox for all using (auth.uid() = user_id or user_id is null) with check (auth.uid() = user_id);
