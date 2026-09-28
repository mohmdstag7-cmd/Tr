-- 002_views.sql — Views for analytics and reporting

-- v_trade_full: enriched trade view joining trades + signals + strategy_configs + account snapshots
CREATE VIEW IF NOT EXISTS v_trade_full AS
SELECT
    t.id AS trade_id,
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
    (COALESCE(t.profit,0) + COALESCE(t.swap,0) + COALESCE(t.commission,0)) AS net_profit,
    t.strategy,
    t.status,
    t.magic,
    t.signal_id,
    s.time AS signal_time,
    s.direction AS signal_direction,
    s.price AS signal_price,
    s.confidence AS signal_confidence,
    sc.name AS strategy_name,
    sc.version AS strategy_version,
    sc.params AS strategy_params
FROM trades t
LEFT JOIN signals s ON s.id = t.signal_id
LEFT JOIN strategy_configs sc ON sc.id = t.strategy_config_id;

-- v_daily_performance: daily aggregation from trades
CREATE VIEW IF NOT EXISTS v_daily_performance AS
SELECT
    date(COALESCE(close_time, open_time)) AS day,
    COUNT(*) AS trade_count,
    SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) AS win_count,
    SUM(CASE WHEN profit < 0 THEN 1 ELSE 0 END) AS loss_count,
    SUM(profit) AS total_profit,
    SUM(swap) AS total_swap,
    SUM(commission) AS total_commission,
    SUM(COALESCE(profit,0) + COALESCE(swap,0) + COALESCE(commission,0)) AS net_profit,
    AVG(profit) AS avg_profit,
    MAX(profit) AS max_profit,
    MIN(profit) AS min_profit
FROM trades
WHERE status = 'closed'
GROUP BY date(COALESCE(close_time, open_time));

-- v_performance_by_bucket: aggregation of performance_metrics by bucket and metric
CREATE VIEW IF NOT EXISTS v_performance_by_bucket AS
SELECT
    bucket,
    metric,
    date(time) AS day,
    COUNT(*) AS sample_count,
    AVG(value) AS avg_value,
    MIN(value) AS min_value,
    MAX(value) AS max_value,
    SUM(value) AS sum_value
FROM performance_metrics
GROUP BY bucket, metric, date(time);

-- v_strategy_config_compare: compare strategy configs by linked trades and backtest runs
CREATE VIEW IF NOT EXISTS v_strategy_config_compare AS
SELECT
    sc.id AS strategy_config_id,
    sc.name,
    sc.version,
    sc.params,
    sc.is_active,
    COUNT(DISTINCT t.id) AS trade_count,
    COUNT(DISTINCT br.id) AS backtest_count,
    AVG(t.profit) AS avg_trade_profit,
    SUM(t.profit) AS total_trade_profit,
    MAX(br.results) AS last_backtest_results
FROM strategy_configs sc
LEFT JOIN trades t ON t.strategy_config_id = sc.id AND t.status = 'closed'
LEFT JOIN backtest_runs br ON br.strategy_config_id = sc.id
GROUP BY sc.id, sc.name, sc.version, sc.params, sc.is_active;
