-- supabase/cleanup.sql — Aggregation + cleanup functions

-- Aggregate daily performance into daily_reports (idempotent)
create or replace function public.aggregate_daily_reports(target_date date default current_date - interval '1 day')
returns int as $$
declare
  inserted int := 0;
begin
  insert into public.daily_reports (user_id, date, content, metrics)
  select
    t.user_id,
    target_date,
    'Auto-aggregated daily report for ' || target_date::text,
    jsonb_build_object(
      'trade_count', count(*),
      'win_count', count(*) filter (where profit > 0),
      'loss_count', count(*) filter (where profit < 0),
      'total_profit', coalesce(sum(profit),0),
      'net_profit', coalesce(sum(profit + coalesce(swap,0) + coalesce(commission,0)),0)
    )
  from public.trades t
  where t.status = 'closed' and (coalesce(t.close_time, t.open_time))::date = target_date
  group by t.user_id
  on conflict (date) do update set metrics = excluded.metrics, content = excluded.content
  ;
  get diagnostics inserted = row_count;
  return inserted;
end;
$$ language plpgsql security definer;

-- Cleanup old logs: keep 90 days of app_logs, 30 days of mt5_requests, 180 days of health_checks
create or replace function public.cleanup_old_logs()
returns table(deleted_app_logs int, deleted_mt5_requests int, deleted_health_checks int) as $$
declare
  c1 int; c2 int; c3 int;
begin
  delete from public.app_logs where created_at < now() - interval '90 days';
  get diagnostics c1 = row_count;
  delete from public.mt5_requests where created_at < now() - interval '30 days';
  get diagnostics c2 = row_count;
  delete from public.health_checks where created_at < now() - interval '180 days';
  get diagnostics c3 = row_count;
  -- Also purge synced outbox older than 7 days
  delete from public.outbox where status = 'synced' and synced_at < now() - interval '7 days';
  return query select c1, c2, c3;
end;
$$ language plpgsql security definer;

-- Cleanup orphaned snapshots / metrics older than 1 year (keep aggregated daily_reports)
create or replace function public.cleanup_old_snapshots(retention_days int default 365)
returns int as $$
declare
  deleted int;
begin
  delete from public.account_snapshots where time < now() - (retention_days || ' days')::interval;
  get diagnostics deleted = row_count;
  delete from public.performance_metrics where time < now() - (retention_days || ' days')::interval;
  return deleted;
end;
$$ language plpgsql security definer;

-- Vacuum / analyze helper (to be called via cron)
create or replace function public.maintenance_vacuum()
returns void as $$
begin
  -- Supabase cron should call this; actual VACUUM cannot run inside function transaction,
  -- so we just ANALYZE
  execute 'analyze public.trades';
  execute 'analyze public.signals';
  execute 'analyze public.account_snapshots';
end;
$$ language plpgsql security definer;
