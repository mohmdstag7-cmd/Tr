"""SQLite database with WAL, migrations, backup and singleton access."""

from __future__ import annotations

import contextlib
import shutil
import sqlite3
import threading
from collections.abc import Generator
from pathlib import Path

try:
    from app.observability.logger import get_logger  # type: ignore[import-not-found]

    _logger = get_logger(__name__)
except Exception:  # pragma: no cover - fallback when observability not available in tests
    import logging

    _logger = logging.getLogger(__name__)


def _default_db_path() -> Path:
    """Return platform-specific default DB path."""
    import os
    import sys

    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
        return base / "MT5TradingWorkstation" / "mt5tw.db"
    return Path.home() / ".mt5tw" / "mt5tw.db"


class Database:
    """SQLite wrapper with WAL mode, foreign keys and migration support."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path: Path = Path(db_path) if db_path else _default_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._lock = threading.RLock()
        self._connect()

    def _connect(self) -> None:
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False, isolation_level=None, detect_types=sqlite3.PARSE_DECLTYPES)
        self._conn.row_factory = sqlite3.Row
        # Critical pragmas per spec
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")
        _logger.info("database_connected", extra={"db_path": str(self.db_path)})

    @contextlib.contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Yield a connection with thread-safety. Caller should not close it."""
        if self._conn is None:
            self._connect()
        assert self._conn is not None
        with self._lock:
            yield self._conn

    def backup(self, target_path: Path | str) -> Path:
        """Copy DB file to target_path before migration. Returns target path."""
        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            # Ensure WAL checkpoint before copy
            if self._conn is not None:
                try:
                    self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                except sqlite3.Error:
                    pass
            shutil.copy2(str(self.db_path), str(target))
        _logger.info("database_backup_created", extra={"target": str(target)})
        return target

    def migrate(self) -> list[str]:
        """Run all SQL files in app/storage/migrations/ in order.

        Tracks applied migrations in _migrations table. Performs pre-migration backup.
        Returns list of newly applied filenames.
        """
        migrations_dir = Path(__file__).parent / "migrations"
        migrations_dir.mkdir(parents=True, exist_ok=True)

        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS _migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT UNIQUE NOT NULL,
                    applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                );
                """
            )
            rows = conn.execute("SELECT filename FROM _migrations ORDER BY filename").fetchall()
            applied = {r["filename"] for r in rows}

            files = sorted([p for p in migrations_dir.glob("*.sql") if p.is_file()])
            pending = [p for p in files if p.name not in applied]

            if pending:
                # Pre-migration backup (forward-only, pre-migration backup per spec)
                backup_path = self.db_path.with_suffix(f".pre_{pending[0].stem}.bak")
                try:
                    self.backup(backup_path)
                except Exception as exc:  # pragma: no cover
                    _logger.warning("database_backup_failed", extra={"error": str(exc)})

            newly_applied: list[str] = []
            for sql_file in pending:
                sql_text = sql_file.read_text(encoding="utf-8")
                _logger.info("applying_migration", extra={"filename": sql_file.name})
                try:
                    conn.executescript(sql_text)
                    conn.execute("INSERT INTO _migrations (filename) VALUES (?)", (sql_file.name,))
                    conn.commit()
                    newly_applied.append(sql_file.name)
                    _logger.info("migration_applied", extra={"filename": sql_file.name})
                except sqlite3.Error as exc:
                    conn.rollback()
                    _logger.error("migration_failed", extra={"filename": sql_file.name, "error": str(exc)})
                    raise
            return newly_applied

    def close(self) -> None:
        """Close underlying connection."""
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                finally:
                    self._conn = None
                _logger.info("database_closed", extra={"db_path": str(self.db_path)})


# Singleton
_instance: Database | None = None
_instance_lock = threading.Lock()


def get_database(db_path: Path | None = None) -> Database:
    """Lazily initialize singleton Database. Thread-safe."""
    global _instance
    if _instance is not None and db_path is None:
        return _instance
    with _instance_lock:
        if _instance is None:
            _instance = Database(db_path=db_path)
            # Auto-migrate on first init
            try:
                _instance.migrate()
            except Exception as exc:  # pragma: no cover
                _logger.warning("auto_migrate_failed", extra={"error": str(exc)})
        elif db_path is not None and db_path != _instance.db_path:
            # For testing: allow override path by resetting singleton
            _instance.close()
            _instance = Database(db_path=db_path)
            _instance.migrate()
    return _instance


def _reset_database_for_tests() -> None:  # pragma: no cover - test helper
    global _instance
    with _instance_lock:
        if _instance is not None:
            _instance.close()
            _instance = None
