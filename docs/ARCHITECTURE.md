# Architecture — MT5 Trading Workstation

> Load-bearing architectural decisions (ADR-style). These decisions are intentional and constrain all future phases. See `docs/SPEC.md` Part D2 / D3 for full rationale.

## ADR-001: Python 3.11 + Windows-Only

**Context:** MetaTrader 5 terminal and the official `MetaTrader5` Python package are Windows-only. The workstation must interact with a locally installed MT5 terminal via IPC. Supporting macOS/Linux would require Wine/unsupported bridges and would break packaging, auto-update, and credential storage assumptions.

**Decision:** Target **Python 3.11 (64-bit) on Windows 10/11 only**. `requires-python = ">=3.11,<3.12"` is enforced in `pyproject.toml`. CI and PyInstaller builds run on `windows-latest`. No cross-platform abstraction is attempted.

**Consequences:**
- Positive: Deterministic environment, single installer path, can rely on Windows Credential Manager, Win32 single-instance mutex, and MT5 terminal path conventions.
- Negative: No native macOS/Linux support. Contributors must develop on Windows or use a Windows VM/CI.
- All dependencies are pinned against Python 3.11 wheels (notably `numpy==1.26.4` to avoid NumPy 2 ABI breakage).

## ADR-002: MT5Gateway — Single-Thread Owner of All MT5 Calls

**Context:** The `MetaTrader5` Python module is not thread-safe and the MT5 terminal allows only one authenticated session per process. Concurrent calls from UI, strategy engine, and data collectors cause race conditions, deadlocks, and silent `last_error` overwrites.

**Decision:** All MT5 API calls go through a single `MT5Gateway` object that owns a dedicated worker thread (QThread). No other module imports `MetaTrader5` directly. Calls are serialized via a request queue; results/errors are returned via signals/futures. UI and domain code never call MT5 synchronously.

**Consequences:**
- Positive: Thread safety by construction, single place to handle `initialize`/`login`/`shutdown`, retry, and `last_error` mapping. Enables deterministic testing via `FakeMT5`.
- Negative: All MT5 operations are asynchronous from the caller's perspective; callers must handle async results. Gateway becomes a bottleneck if not kept non-blocking.
- Enforced by `mypy` import linter and code review: `import MetaTrader5` is allowed only in `app/mt5/gateway.py`.

## ADR-003: Closed-Bar Driven Execution

**Context:** Intra-bar tick strategies introduce look-ahead bias, repainting, and non-determinism between live, paper, and backtest. For auditability and parity across modes, decisions must be reproducible.

**Decision:** The system is **closed-bar driven**. Strategies receive `on_bar_close(symbol, timeframe, closed_bar)` only after a bar is confirmed closed. No `on_tick` trading logic. Indicators are computed on closed bars only.

**Consequences:**
- Positive: Eliminates look-ahead bias, makes backtest ↔ live parity achievable, simplifies idempotency and crash recovery.
- Negative: Cannot implement true tick-scalping strategies; latency is at least one bar. UI may still display live ticks for visualization only.
- Backtest engine replays bars in the same order and calls the same strategy entry point.

## ADR-004: One Broker Interface for Live / Paper / Backtest

**Context:** Duplicating order logic for live, paper, and backtest leads to divergence and untestable risk checks. Risk rules (paper-by-default, server-side SL) must apply uniformly.

**Decision:** Define a single `Broker` abstract interface (`app/broker/interface.py`) with methods `place_order`, `cancel_order`, `positions`, `history`, etc. Three implementations: `LiveBroker` (via `MT5Gateway`), `PaperBroker` (in-memory + SQLite), `BacktestBroker` (event-driven simulation). Strategy code depends only on `Broker`.

**Consequences:**
- Positive: Strategies are broker-agnostic; risk middleware can wrap any implementation; testing can swap `PaperBroker`/`BacktestBroker` without code changes.
- Negative: Interface must be expressive enough for MT5 specifics (filling modes, deviation, magic) while remaining simulatable. Leaky abstractions must be reviewed carefully.

## ADR-005: SQLite as Source of Truth + Supabase Outbox Sync

**Context:** The workstation must work offline, survive crashes, and never lose trades/journal entries. Direct cloud writes would block the UI and risk data loss on network failure.

**Decision:** **SQLite is the local source of truth** for all durable state (trades, orders, bars, journal, config snapshots). Supabase is a secondary replica. Writes go to SQLite first; an `outbox` table queues changes for async sync via `httpx` + `supabase` client. Sync is eventually consistent and retryable.

**Consequences:**
- Positive: Offline-first, crash-safe (WAL + fsync), single source of truth for restores, simple backup (copy `.db` file). Supabase outage does not block trading.
- Negative: Requires outbox pattern, conflict resolution (last-write-wins with server timestamp), and periodic reconciliation. SQLite WAL files (`*.db-shm`, `*.db-wal`) must be handled in backup/ignore rules.

## ADR-006: Pydantic v2 for Configuration

**Context:** Configuration comes from YAML, env vars, and UI forms. Manual validation is error-prone and secrets risk being logged.

**Decision:** Use **Pydantic v2 + pydantic-settings** for all config. Schemas live in `app/config/`. YAML is loaded via `PyYAML` then validated by Pydantic. Secrets use `SecretStr` and are never serialized to logs/exports.

**Consequences:**
- Positive: Strict typing, validation errors at startup, auto-generated JSON Schema for UI forms, safe secret handling.
- Negative: Pydantic v2 breaking changes must be tracked; YAML structure must match schema exactly.

## ADR-007: Loguru for Structured Logging

**Context:** Debugging live trading issues requires correlated, structured logs with rotation and crash reports, without blocking the UI thread.

**Decision:** Use **loguru** as the sole logging library. JSON-structured logs to `logs/app.log` with rotation (10 MB × 5), plus human-readable console sink in dev. All logs include `correlation_id`, `account`, and `symbol` context where applicable. Secrets are masked via filter.

**Consequences:**
- Positive: Single logging API, async-safe sinks, easy redaction, consistent format for support bundles.
- Negative: Standard library `logging` interop must be bridged (intercept handler) for third-party libs.

## ADR-008: PySide6 + pyqtgraph for UI

**Context:** Need a native desktop UI with high-performance candlestick/indicator charts, docking, and Windows packaging. Web-based UIs add complexity and latency.

**Decision:** Use **PySide6 (Qt 6)** for windowing/widgets and **pyqtgraph** for charts. Styling via QSS generated from design tokens. No QML, no Electron.

**Consequences:**
- Positive: Native look & feel, hardware-accelerated charts, single Python process, PyInstaller support is mature for PySide6.
- Negative: Qt threading rules must be respected (UI only on main thread, no blocking calls). `pyqtgraph` API is low-level and requires custom candlestick items.

## ADR-009: Design Tokens → QSS

**Context:** Hard-coded colors/spacing in QSS leads to inconsistency and makes theming impossible. Design changes would require hunting through widgets.

**Decision:** Define **design tokens** in `app/ui/tokens/` (colors, spacing, typography, radii, shadows) as Python constants / JSON. A build step generates `app/ui/styles.qss` from tokens. Widgets reference tokens only.

**Consequences:**
- Positive: Single source of truth for visual design, deterministic QSS generation, easy dark/light theme support later.
- Negative: Token changes require regeneration; contributors must not edit `.qss` by hand.

## ADR-010: FakeMT5 Only in Tests

**Context:** Real MT5 requires a running terminal, credentials, and network. Tests must be deterministic and CI-friendly, but shipped code must never simulate trades as real.

**Decision:** Provide a `FakeMT5` in-memory stub that implements the `MetaTrader5` surface used by `MT5Gateway`. **FakeMT5 is allowed only in `tests/`** (enforced by import lint and `pyproject.toml` per-file ignores). Shipped app (`app/`) uses only the real `MetaTrader5` package via `MT5Gateway`.

**Consequences:**
- Positive: Fast, deterministic unit/integration tests without MT5 installed; no risk of shipping a simulator as live execution.
- Negative: Fake must be kept in sync with real MT5 behavior; integration tests against real terminal remain manual and are marked `pytest.mark.mt5`.

---

*All decisions are load-bearing. Changing them requires an ADR amendment and approval per `docs/SPEC.md` Part A.*
