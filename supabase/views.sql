-- supabase/views.sql — PostgreSQL views (mirrors SQLite views with pg types)

create or replace view public.v_trade_full as
select
  t.id as trade_id,
  t.ticket,
  t.symbol,
  t.mode,
  t.side,
  t.volume,
  t.open_price,
  t.close_price,
  t.sl,
  t.tp,
  t.open_time,
  t.close_time,
  t.profit,
  t.swap,
  t.commission,
  (coalesce(t.profit,0) + coalesce(t.swap,0) + coalesce(t.commission,0)) as net_profit,
  t.strategy,
  t.status,
  t.magic,
  t.signal_id,
  s.time as signal_time,
  s.direction as signal_direction,
  s.price as signal_price,
  s.confidence as signal_confidence,
  sc.name as strategy_name,
  sc.version as strategy_version,
  sc.params as strategy_params
from public.trades t
left join public.signals s on s.id = t.signal_id
left join public.strategy_configs sc on sc.id = t.strategy_config_id;

create or replace view public.v_daily_performance as
select
  (coalesce(close_time, open_time))::date as day,
  count(*) as trade_count,
  count(*) filter (where profit > 0) as win_count,
  count(*) filter (where profit < 0) as loss_count,
  sum(profit) as total_profit,
  sum(swap) as total_swap,
  sum(commission) as total_commission,
  sum(coalesce(profit,0) + coalesce(swap,0) + coalesce(commission,0)) as net_profit,
  avg(profit) as avg_profit,
  max(profit) as max_profit,
  min(profit) as min_profit
from public.trades
where status = 'closed'
group by (coalesce(close_time, open_time))::date;

create or replace view public.v_performance_by_bucket as
select
  bucket,
  metric,
  time::date as day,
  count(*) as sample_count,
  avg(value) as avg_value,
  min(value) as min_value,
  max(value) as max_value,
  sum(value) as sum_value
from public.performance_metrics
group by bucket, metric, time::date;

create or replace view public.v_strategy_config_compare as
select
  sc.id as strategy_config_id,
  sc.name,
  sc.version,
  sc.params,
  sc.is_active,
  count(distinct t.id) as trade_count,
  count(distinct br.id) as backtest_count,
  avg(t.profit) as avg_trade_profit,
  sum(t.profit) as total_trade_profit,
  max(br.results) as last_backtest_results
from public.strategy_configs sc
left join public.trades t on t.strategy_config_id = sc.id and t.status = 'closed'
left join public.backtest_runs br on br.strategy_config_id = sc.id
group by sc.id, sc.name, sc.version, sc.params, sc.is_active;
