# Progress — MT5 Trading Workstation

> Living status document. Updated in every PR. See `docs/SPEC.md` Part G3 for acceptance criteria.

## Current Phase

**Phase 2 — Observability** — *In Progress*

## Phase Table

| Phase | Name | Status | Exit Criteria (G3) |
|------:|------|--------|---------------------|
| 1 | Foundation | **Done** | Repo meta + tooling + design tokens + main window shell + sidebar + empty pages + command palette + in-app auto-updater; lint/type/test green on Windows; CI green; GitHub Release v0.1.0 published |
| 2 | Observability | **In Progress** | Structured loguru logging with categories + trace IDs + secrets masking + crash handler + watchdog + basic Logs page + Health page |
| 3 | MT5 Connection (real) | Not Started | Gateway thread on real MetaTrader5; FakeMT5 in tests/fakes/; test-connection checklist; account profiles; investor mode; symbols; status bar; request logging; Connection Diagnostics; `mt5_smoke_test` script |
| 4 | Storage | Not Started | SQLite + migrations; outbox; Supabase schema/views/RLS/auth; sync status; audit log; history import |
| 5 | Market Data & Analysis | Not Started | Data + sanity checks; broker time; all C3 modules; chart; Market page; calendar + MQL5 exporter |
| 6 | Strategies & Signals | Not Started | Interface; 2 strategies; pipeline; state machine; decision traces; scanner; Signals page |
| 7 | Risk | Not Started | Sizing; limits; exposure; margin; persisted state; Risk page; profiles |
| 8 | Execution | Not Started | Paper broker; live broker; retcode policy; position manager; recovery; deal sync; semi-auto approval; kill switch; `mt5_trade_test` script |
| 9 | Simple Mode (F0/B3b) | Not Started | Simple/Advanced switch; Home screen; Trade Suggestion Card; Details expander; open trades list; plain-language status line; Stop trading button; onboarding branch |
| 10 | Backtesting | Not Started | Engine; costs; metrics; walk-forward; Monte-Carlo; sensitivity; equality test; Backtest page |
| 11 | ML | Not Started | Labeler; features; trainer subprocess; calibration; SHAP; registry; drift; Model page; pipeline integration |
| 12 | Analytics & Journal | Not Started | Dashboard; Positions & Trades; Analytics; Journal; daily/weekly reports; notifications; Telegram |
| 13 | AI Loop & Go-Live | Not Started | Export; import; diff; auto-backtest; config compare; Go-Live gate; optional LLM |
| 14 | Reliability | Not Started | Health page; metrics; debug bundle; full Logs page; 24h soak test on demo |
| 15 | In-App Auto-Update | Not Started | Release feed check; background download; checksum verification; silent install + relaunch; rollback; update logging |
| 16 | Release | Not Started | Persian/RTL; light theme; polish; accessibility; full tests; README/USER_GUIDE; PyInstaller + Inno Setup |

*Status values: Not Started | In Progress | In Review | Done*

## Completed (Phase 1)

- [x] Repo scaffolding: `pyproject.toml` (pinned deps), `.pre-commit-config.yaml`, `.editorconfig`, `.gitignore`
- [x] Docs: `SPEC.md`, `ARCHITECTURE.md`, `PROGRESS.md`, `README.md`, `CHANGELOG.md`, `AGENTS.md` (= `CLAUDE.md` = `.github/copilot-instructions.md`), `SECURITY.md`, `LICENSE`
- [x] GitHub workflows: `ci.yml` (ruff + mypy + pytest on windows-latest), `build.yml` (PyInstaller + `--self-check` + upload artifact), `release-please.yml`, `release.yml` (with `latest.json` + `latest` moving tag), `codeql.yml`
- [x] Issue templates (bug with debug-bundle callout, feature, phase task), PR template, Dependabot config
- [x] `app/__version__.py` (single source of truth, bumped by release-please)
- [x] `app/main.py` with `--version`, `--self-check`, `--mt5-smoke-test`, `--mt5-trade-test`, `--profile` flags
- [x] `app/core/`: event_bus (thread-safe pub/sub), clock (system + FixedClock), di (minimal container), profiles (per-account YAML), config (AppSettings JSON), single_instance (cross-process file lock)
- [x] `app/ui/theme/`: dark + light Tokens (frozen dataclass) per F1 palette; `generate_qss(tokens)` → full QSS
- [x] `app/ui/i18n/`: EN + FA translations; `tr(key, default=None, **kwargs)` with fallback to default
- [x] `app/ui/widgets/`: KpiCard, ProbabilityRing (donut + CI + sample size), Badge, Toggle, DataTable, Drawer, Toast, EmptyState, ErrorState, ConfirmDialog (with typed confirmation)
- [x] `app/ui/`: MainWindow (top bar + sidebar + stacked pages + status bar + Ctrl+K), Sidebar (14 page buttons in 3 groups), StatusBar (rich + simple-mode collapse), CommandPalette (18 commands), 14 page stubs (Dashboard, Market, Signals, PositionsTrades, Analytics, Journal, Backtest, Model, AiLab, Strategies, Risk, Logs, Health, Settings)
- [x] `app/updater/`: in-app auto-updater (Part J) — UpdateChecker, UpdateWorker (QThread), ReleaseFeed (GitHub Releases API + tag_name discovery), Downloader (streaming + SHA-256 verify), Installer (Inno Setup `/VERYSILENT` + relaunch + rollback)
- [x] `app/ui/widgets/update_banner.py` + `app/ui/dialogs/update_dialog.py` (with typed confirmation for breaking updates)
- [x] Settings page integrated with Updates section + UpdateBanner
- [x] MainWindow auto-checks for updates 5s after startup if `check_updates_on_startup=True`
- [x] `scripts/build.py` (PyInstaller wrapper), `scripts/mt5_smoke_test.py`, `scripts/installer.iss` (Inno Setup template)
- [x] Tests: 55 passing (smoke + main_window + pages + widgets + single_instance + event_bus + clock + updater)
- [x] GitHub Release v0.1.0 published with `latest.json`, installer, zip, checksums.txt
- [x] All CI checks green: CodeQL, lint-type-test, analyze, build-windows

## In Progress (Phase 2)

- [ ] `app/observability/logger.py` — loguru setup with categories, JSON format, non-blocking enqueue, rotation
- [ ] `app/observability/context.py` — session_id, trace_id context vars (ContextVar)
- [ ] `app/observability/masking.py` — secrets redaction filter (passwords, API keys, account numbers)
- [ ] `app/observability/decision_trace.py` — per-signal decision trace as a readable checklist
- [ ] `app/observability/crash_handler.py` — sys.excepthook + threading.excepthook + Qt message handler → `crash_reports/crash_<time>.json` with stack + last 200 log lines
- [ ] `app/observability/watchdog.py` — worker heartbeats; freeze > Ns → CRITICAL + restart
- [ ] `app/observability/audit.py` — every user action + setting change (before → after) as JSON
- [ ] `app/observability/health.py` — MT5 connected, Algo Trading on, quotes fresh, broker offset, Supabase reachable, sync queue, disk, log size, internet latency, PC clock drift (some checks stubbed for Phase 2 — real MT5 check in Phase 3)
- [ ] `app/observability/metrics.py` — CPU, RAM, bar-processing latency, MT5 call latency p50/p95, queue sizes; WARNING above budgets (D4)
- [ ] `app/observability/debug_bundle.py` — zip of recent logs, crash reports, masked settings, health, versions, last N decision traces + `README_DEBUG.md` with AI prompt
- [ ] `app/ui/pages/logs.py` — Logs page UI: category tabs, live tail, filters (level/category/symbol/strategy/time/regex), JSON detail, full trace view, change level, debug mode, export, open folder
- [ ] `app/ui/pages/health.py` — Health page UI: checks, performance metrics, worker status, debug bundle button
- [ ] `app/main.py` — wire crash handler at startup
- [ ] Tests for: logger, masking (passwords not in logs), crash handler (forced exception produces a crash report), watchdog, audit, decision_trace, debug_bundle

## Known Issues

- None yet for Phase 1 (closed).
- Phase 2 known limitation: the MT5-connected health check will return "unknown" until Phase 3 wires up the real MT5Gateway. The check is stubbed to return `HealthStatus.UNKNOWN` rather than fail.

## Next — Phase 3 (MT5 Connection, real)

Per SPEC Part G3, Phase 3 will deliver:

- The real `MetaTrader5` package wrapped in a single-thread `MT5Gateway` with a command queue
- `FakeMT5` simulator under `tests/fakes/` (used by pytest + CI, never shipped)
- The first-run connection wizard (auto-detect terminal64.exe, login, server, live checklist)
- Account profiles (login + server + terminal_path), investor password → Analysis-only mode
- Symbol cache + spec reader (digits, point, contract size, volume step, stops level, filling modes)
- StatusBar populated with real values (broker, login, balance, equity, live bid/ask)
- `mt5_smoke_test` script + `--mt5-smoke-test` CLI flag (read-only, 30s verification)
- Connection Diagnostics page/button with "Copy report"

## Narrative

Phase 1 is closed and merged via PR #9. The user explicitly asked for the in-app auto-updater before downloading the first 300MB build, so we added the full Part J updater pipeline + GitHub Release v0.1.0 + `latest.json` feed in the same phase. The user can now update to v0.2.0+ with one click from inside the app — no manual re-download.

Phase 2 (Observability) is the foundation for everything that follows. Every later phase depends on having structured logs with trace IDs that follow a signal from bar evaluation → strategy → risk → execution → close → sync. Without it, debugging distributed across MT5 + Supabase + worker threads is impossible. Phase 2 also delivers the crash handler, secrets masking, and the Logs/Health pages that the user will use to file bug reports with debug bundles.

*Last updated: Phase 2 start*
