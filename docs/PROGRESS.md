# Progress — MT5 Trading Workstation

> Living status document for Phase 1 (Foundation). Updated in every PR. See `docs/SPEC.md` Part G3 for acceptance criteria.

## Current Phase

**Phase 1 — Foundation** — *In Progress (Batch 1)*

## Phase Table

| Phase | Name | Status | Entry Criteria | Exit Criteria (G3) |
|------:|------|--------|----------------|---------------------|
| 1 | Foundation | **In Progress** | Repo created, SPEC approved | Repo meta + tooling + design tokens + main window shell + sidebar + empty pages + command palette; lint/type/test green on Windows |
| 2 | Observability | Not Started | Phase 1 accepted | Structured logging, crash reports, health checks, log viewer |
| 3 | Data & Market Data | Not Started | Phase 2 accepted | Bar store, SQLite schema, MT5 history sync, closed-bar feed |
| 4 | Broker & Execution | Not Started | Phase 3 accepted | Broker interface, Live/Paper brokers, server-side SL, paper-by-default |
| 5 | Risk & Money Management | Not Started | Phase 4 accepted | Risk middleware, position sizing, daily loss limits |
| 6 | Strategy Engine | Not Started | Phase 5 accepted | Closed-bar strategy API, lifecycle, domain purity |
| 7 | Backtesting | Not Started | Phase 6 accepted | BacktestBroker, parity with live, performance metrics |
| 8 | Optimization & Walk-Forward | Not Started | Phase 7 accepted | Parameter search, walk-forward, overfit guards |
| 9 | Machine Learning | Not Started | Phase 8 accepted | LightGBM pipeline, SHAP, feature store |
| 10 | Journal & Analytics | Not Started | Phase 9 accepted | Trade journal, analytics views, exports |
| 11 | Alerts & Notifications | Not Started | Phase 10 accepted | Alert engine, desktop notifications |
| 12 | Supabase Sync & Cloud | Not Started | Phase 11 accepted | Outbox sync, auth, cloud backup |
| 13 | Auto-Update & Packaging | Not Started | Phase 12 accepted | PyInstaller bundle, updater (Part J), signed installer |
| 14 | Security Hardening | Not Started | Phase 13 accepted | Credential audit, secret redaction, single instance |
| 15 | Performance & Reliability | Not Started | Phase 14 accepted | Profiling, crash safety, idempotency |
| 16 | Release & Polish | Not Started | Phase 15 accepted | Docs, onboarding, final QA, tagged release |

*Status values: Not Started | In Progress | In Review | Done*

## Completed (Phase 1 — Batch 1)

- [x] Repository scaffolding and foundation setup
- [x] GitHub workflows (CI: lint, type, test on Windows)
- [x] Design tokens → QSS pipeline stub
- [x] Main window shell (PySide6)
- [x] Sidebar navigation
- [x] Empty pages for all 16 phases (placeholders)
- [x] Command palette (Ctrl+K) skeleton
- [x] Tooling: `pyproject.toml` (pinned deps), `.pre-commit-config.yaml`, `.editorconfig`, `.gitignore`
- [x] Docs: `README.md`, `docs/ARCHITECTURE.md`, `docs/PROGRESS.md`, `CHANGELOG.md`, `AGENTS.md`, `SECURITY.md`, `LICENSE`
- [x] Version module `app/__version__.py`

## In Progress

- Main window wiring to real navigation and QSS application
- Pre-commit hook verification on Windows
- CI workflow file finalization under `.github/workflows/`

## Known Issues

*None* — Foundation has no runtime trading logic yet. Any deviation from SPEC Part G3 will be listed here.

## Next — Phase 2 (Observability)

Per SPEC Part G3, Phase 2 will deliver:

- `loguru` structured logging with rotation and secret masking
- Crash report generation under `crash_reports/`
- Health checks (MT5 terminal, disk, memory via `psutil`)
- In-app log viewer page
- Correlation IDs across gateway → broker → strategy

## Narrative

Phase 1 establishes the non-negotiable foundation: Windows-only Python 3.11, single-thread `MT5Gateway`, closed-bar execution, one `Broker` interface, SQLite + outbox, Pydantic v2 config, PySide6 + pyqtgraph, and `FakeMT5` test isolation. Batch 1 focuses on repo-meta, tooling, and the UI shell so that subsequent phases can land incrementally behind a green CI gate. No trading logic ships in Phase 1.

*Last updated: 2025-12-09 — Phase 1 Batch 1*
