"""Tests for Phase 4 Storage — 12+ tests covering DB, migrations, outbox, repos, sync."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock


def test_database_creates_file(db) -> None:
    assert db.db_path.exists()
    assert db.db_path.stat().st_size > 0


def test_database_wal_mode(db) -> None:  # type: ignore[no-untyped-def]
    with db.get_connection() as conn:
        cur = conn.execute("PRAGMA journal_mode;")
        mode = cur.fetchone()[0]
        assert mode.lower() == "wal"
        cur = conn.execute("PRAGMA foreign_keys;")
        assert cur.fetchone()[0] == 1
        cur = conn.execute("PRAGMA synchronous;")
        # NORMAL = 1
        assert cur.fetchone()[0] in (1, 2)


def test_migrations_applied(db) -> None:  # type: ignore[no-untyped-def]
    with db.get_connection() as conn:
        cur = conn.execute("SELECT filename FROM _migrations ORDER BY filename")
        filenames = [r["filename"] for r in cur.fetchall()]
        assert "001_initial_schema.sql" in filenames
        assert "002_views.sql" in filenames


def test_migrations_idempotent(db) -> None:  # type: ignore[no-untyped-def]
    first = db.migrate()
    assert first == []  # no new migrations
    second = db.migrate()
    assert second == []


def test_backup_creates_copy(db, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    target = tmp_path / "backup.db"
    result = db.backup(target)
    assert result.exists()
    assert result.stat().st_size > 0


def test_tables_exist(db) -> None:  # type: ignore[no-untyped-def]
    expected = [
        "accounts",
        "sessions",
        "strategy_configs",
        "signals",
        "decision_traces",
        "trades",
        "trade_events",
        "mt5_requests",
        "account_snapshots",
        "risk_events",
        "model_versions",
        "backtest_runs",
        "journal",
        "audit_log",
        "app_logs",
        "health_checks",
        "performance_metrics",
        "daily_reports",
        "calendar_events",
        "outbox",
    ]
    with db.get_connection() as conn:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {r["name"] for r in cur.fetchall()}
        for t in expected:
            assert t in tables, f"missing table {t}"


def test_indexes_exist(db) -> None:  # type: ignore[no-untyped-def]
    with db.get_connection() as conn:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = {r["name"] for r in cur.fetchall()}
        assert "idx_signals_time_symbol_strategy" in indexes
        assert "idx_trades_open_close_symbol_mode" in indexes
        assert "idx_account_snapshots_time" in indexes
        assert "idx_mt5_requests_created_at" in indexes
        assert "idx_app_logs_time_category_level" in indexes
        assert "idx_audit_log_time" in indexes


def test_views_exist(db) -> None:  # type: ignore[no-untyped-def]
    with db.get_connection() as conn:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='view'")
        views = {r["name"] for r in cur.fetchall()}
        assert "v_trade_full" in views
        assert "v_daily_performance" in views
        assert "v_performance_by_bucket" in views
        assert "v_strategy_config_compare" in views


def test_outbox_enqueue_and_pending(db, outbox) -> None:  # type: ignore[no-untyped-def]
    oid = outbox.enqueue("trades", "rec-1", "insert", {"id": "rec-1", "symbol": "EURUSD"})
    assert oid
    pending = outbox.pending(limit=10)
    assert len(pending) >= 1
    assert any(r["record_id"] == "rec-1" for r in pending)


def test_outbox_mark_synced_and_failed(db, outbox) -> None:  # type: ignore[no-untyped-def]
    oid = outbox.enqueue("signals", "sig-1", "insert", {"id": "sig-1"})
    outbox.mark_synced(oid)
    with db.get_connection() as conn:
        cur = conn.execute("SELECT status FROM outbox WHERE id=?", (oid,))
        assert cur.fetchone()["status"] == "synced"
    oid2 = outbox.enqueue("signals", "sig-2", "insert", {"id": "sig-2"})
    outbox.mark_failed(oid2, "network error")
    with db.get_connection() as conn:
        cur = conn.execute("SELECT status, last_error FROM outbox WHERE id=?", (oid2,))
        row = cur.fetchone()
        assert row["status"] == "failed"
        assert "network error" in row["last_error"]


def test_repository_insert_writes_outbox(db) -> None:  # type: ignore[no-untyped-def]
    from app.storage.repositories import SignalRepository

    repo = SignalRepository(db)
    sid = repo.insert(
        {
            "id": "sig-test-1",
            "time": "2025-01-01T00:00:00Z",
            "symbol": "EURUSD",
            "strategy": "test",
            "direction": "buy",
            "price": 1.1234,
        }
    )
    assert sid == "sig-test-1"
    fetched = repo.get_by_id(sid)
    assert fetched is not None
    assert fetched.symbol == "EURUSD"
    # outbox should have entry
    with db.get_connection() as conn:
        cur = conn.execute("SELECT * FROM outbox WHERE table_name='signals' AND record_id=?", (sid,))
        assert cur.fetchone() is not None


def test_repository_crud_and_models(db) -> None:  # type: ignore[no-untyped-def]
    from app.storage.repositories import TradeRepository

    repo = TradeRepository(db)
    tid = repo.insert(
        {
            "id": "trade-1",
            "symbol": "GBPUSD",
            "mode": "demo",
            "side": "buy",
            "volume": 0.1,
            "status": "open",
        }
    )
    assert repo.count() >= 1
    repo.update(tid, {"status": "closed", "profit": 12.5})
    updated = repo.get_by_id(tid)
    assert updated is not None
    assert updated.status == "closed"
    # to_dict / from_row
    d = updated.to_dict()
    assert d["id"] == tid
    # list
    items = repo.list(limit=10)
    assert len(items) >= 1
    repo.delete(tid)
    assert repo.get_by_id(tid) is None


def test_supabase_sync_process_outbox_success(db) -> None:  # type: ignore[no-untyped-def]
    from app.storage.outbox import Outbox
    from app.storage.supabase_sync import SupabaseSync

    outbox = Outbox(db)
    outbox.enqueue("accounts", "acc-1", "insert", {"id": "acc-1", "login": 12345, "server": "Test"})

    mock_client = MagicMock()
    mock_client.is_configured = True
    mock_client.upsert.return_value = {"data": []}
    mock_client.delete.return_value = {"data": []}

    sync = SupabaseSync(db=db, client=mock_client)
    synced = sync.process_outbox(batch_size=10)
    assert synced >= 1
    assert mock_client.upsert.called
    # pending should be 0 after sync
    assert outbox.count_pending() == 0


def test_supabase_sync_handles_failure(db) -> None:  # type: ignore[no-untyped-def]
    from app.storage.outbox import Outbox
    from app.storage.supabase_sync import SupabaseSync

    outbox = Outbox(db)
    outbox.enqueue("trades", "fail-1", "insert", {"id": "fail-1"})

    mock_client = MagicMock()
    mock_client.is_configured = True
    mock_client.upsert.side_effect = RuntimeError("supabase down")

    sync = SupabaseSync(db=db, client=mock_client)
    synced = sync.process_outbox(batch_size=10)
    assert synced == 0
    with db.get_connection() as conn:
        cur = conn.execute("SELECT status FROM outbox WHERE record_id='fail-1'")
        assert cur.fetchone()["status"] == "failed"


def test_supabase_sync_skips_when_not_configured(db) -> None:  # type: ignore[no-untyped-def]
    from app.storage.outbox import Outbox
    from app.storage.supabase_sync import SupabaseSync

    outbox = Outbox(db)
    outbox.enqueue("journal", "j-1", "insert", {"id": "j-1"})
    mock_client = MagicMock()
    mock_client.is_configured = False
    sync = SupabaseSync(db=db, client=mock_client)
    synced = sync.process_outbox()
    assert synced == 0
    # still pending
    assert outbox.count_pending() >= 1


def test_pydantic_models_to_dict_from_row(db) -> None:  # type: ignore[no-untyped-def]
    from app.storage.models import Account

    acc = Account(id="a1", login=999, server="Demo", name="Test", currency="USD", balance=1000, equity=1000)
    d = acc.to_dict()
    assert d["login"] == 999
    # from_row via sqlite
    with db.get_connection() as conn:
        conn.execute("INSERT INTO accounts (id, login, server, name, currency, balance, equity) VALUES (?,?,?,?,?,?,?)", ("a1", 999, "Demo", "Test", "USD", 1000, 1000))
        conn.commit()
        cur = conn.execute("SELECT * FROM accounts WHERE id='a1'")
        row = cur.fetchone()
        acc2 = Account.from_row(row)
        assert acc2.id == "a1"
        assert acc2.login == 999
