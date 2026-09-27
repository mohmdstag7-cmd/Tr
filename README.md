# MT5 Trading Workstation

A professional desktop trading workstation for **MetaTrader 5** on Windows. It gives you a clean, fast interface to view markets, manage risk, run strategies, and keep a journal — all in one app that talks directly to your MT5 terminal.

This is **not** a broker and **not** a signal service. It connects to *your* MT5 account (live or demo) on *your* computer. Paper trading is the default; live trading requires explicit confirmation and always uses a server-side stop-loss.

> Spec: [`docs/SPEC.md`](docs/SPEC.md) — full requirements and acceptance criteria.
> Progress: [`docs/PROGRESS.md`](docs/PROGRESS.md) — what is done and what is next.

## Requirements

- **Windows 10 or Windows 11** (64-bit)
- **Python 3.11 (64-bit)** — exactly 3.11, not 3.12+ (see `pyproject.toml`)
- **MetaTrader 5 terminal** installed and logged in (from your broker)
- ~500 MB free disk space for the app + data

> Why Windows only? The official MT5 Python package works only on Windows with a local MT5 terminal. See `docs/ARCHITECTURE.md` ADR-001.

## Quick Start

```powershell
# 1) Clone
git clone https://github.com/your-org/mt5-trading-workstation.git
cd mt5-trading-workstation

# 2) Create a virtual environment with Python 3.11
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3) Install in editable mode with dev tools
pip install -e .[dev]

# 4) (optional) Install pre-commit hooks
pre-commit install

# 5) Run the app
mt5-workstation
# or: python -m app.main
```

The app opens a main window with a sidebar and empty pages (Phase 1 shell). No trades are placed on first run — paper mode is default.

## Project Layout

The code lives in `app/` (UI in `app/ui/`, MT5 gateway in `app/mt5/`, broker in `app/broker/`, config in `app/config/`), tests in `tests/` (with `FakeMT5` only there), docs in `docs/`, and GitHub workflows in `.github/workflows/`. SQLite databases, logs, and crash reports are written to the user data directory at runtime and are ignored by git. See `docs/SPEC.md` Part D2 and `docs/ARCHITECTURE.md` for the full architecture.

```
mt5-trading-workstation/
  app/                 # application code
  tests/               # pytest suite (FakeMT5 lives here only)
  docs/                # SPEC, ARCHITECTURE, PROGRESS
  .github/workflows/   # CI
  pyproject.toml       # pinned dependencies & tool config
```

## Roadmap

From `docs/SPEC.md` Part G3 — 16 phases, shipped in order:

1. **Foundation** — repo, tooling, design tokens, main window shell, sidebar, command palette *(current)*
2. **Observability** — structured logging, crash reports, health checks
3. **Data & Market Data** — bar store, SQLite schema, MT5 history sync
4. **Broker & Execution** — Broker interface, Live/Paper brokers, server-side SL
5. **Risk & Money Management** — risk middleware, sizing, daily limits
6. **Strategy Engine** — closed-bar strategy API and lifecycle
7. **Backtesting** — BacktestBroker and parity with live
8. **Optimization & Walk-Forward** — parameter search and overfit guards
9. **Machine Learning** — LightGBM pipeline, SHAP, feature store
10. **Journal & Analytics** — trade journal and analytics views
11. **Alerts & Notifications** — alert engine and desktop notifications
12. **Supabase Sync & Cloud** — outbox sync and cloud backup
13. **Auto-Update & Packaging** — PyInstaller bundle and updater (Part J)
14. **Security Hardening** — credential audit and secret redaction
15. **Performance & Reliability** — profiling, crash safety, idempotency
16. **Release & Polish** — docs, onboarding, final QA

See `docs/PROGRESS.md` for the detailed phase table and current status.

## License

Proprietary — All Rights Reserved. Copyright (c) 2025 MT5 Workstation. No license is granted to copy, modify, or distribute this software. See [`LICENSE`](LICENSE).

## Troubleshooting

**1. MT5 not found / `Failed to initialize MT5`**
Make sure the MT5 terminal is installed and has been opened at least once. The app looks for `terminal64.exe` in the default install path. Open MT5 manually, log in, and enable `Tools → Options → Expert Advisors → Allow algorithmic trading`. Then restart the workstation.

**2. Wrong password / `Authorization failed`**
Credentials are stored in Windows Credential Manager (via `keyring`), not in files. If login fails, open `Credential Manager → Windows Credentials` and remove any `mt5-workstation` entry, then re-enter the password in the app. Check that the server name matches exactly (e.g., `MetaQuotes-Demo`).

**3. Algo Trading off / orders rejected**
In MT5 terminal, ensure the `Algo Trading` button in the toolbar is green (on). Also check `Tools → Options → Expert Advisors → Allow DLL imports` if the strategy requires it. The workstation will show a banner if algo trading is disabled.

**4. Antivirus false positive on the build (`mt5-workstation.exe`)**
PyInstaller bundles can trigger heuristic warnings. This is a known false positive. Add the install folder to your antivirus exclusions, or build from source with `pip install -e .` and run `mt5-workstation` via Python. The signed installer (Phase 13) will reduce this.

**5. NumPy 2 vs 1 conflict (`numpy 2.x is installed but 1.26.4 is required`)**
This project pins `numpy==1.26.4` for compatibility with `MetaTrader5` and `lightgbm` wheels on Python 3.11. If you have NumPy 2 installed, recreate the venv: `pip uninstall -y numpy && pip install "numpy==1.26.4"` or `pip install -e .[dev] --force-reinstall`.

Still stuck? Check `logs/app.log` and `crash_reports/` (if present) and include the relevant lines when opening an issue. Never paste passwords or account numbers — they are masked in logs by design.
