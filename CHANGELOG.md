# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- In-app auto-updater: checks GitHub Releases for newer versions, downloads the installer, verifies SHA-256, and silently installs + relaunches (Part J). Includes UpdateBanner widget, UpdateDialog with progress, semver comparison, and rollback-to-previous-installer support.
- Phase 2 (Observability) — in progress:
  - Structured JSON logging via `loguru` with non-blocking `enqueue=True`; per-category log files (`logs/<category>/<date>.jsonl`) + readable `logs/all.log`; rotation, compression, retention (30 days), total size cap.
  - Trace IDs via `ContextVar` follow a signal from bar evaluation → close → sync.
  - Secrets masking filter: passwords, API keys, account numbers, Supabase keys are redacted in logs, exports, and debug bundles.
  - Crash handler: `sys.excepthook`, `threading.excepthook`, Qt message handler → `crash_reports/crash_<time>.json` (stack + last 200 log lines + state + versions + OS) + friendly dialog.
  - Watchdog: worker heartbeats; freeze > Ns → CRITICAL + restart worker.
  - Decision trace per signal as a readable checklist (`probability 0.63 ≥ 0.60 ✓ | spread 1.8 ≤ 2.5 ✓ | news USD CPI in 12 min ✗ → REJECTED`).
  - Audit log: every user action + setting change (before → after) as JSON.
  - Health checks: MT5 connected, Algo Trading on, quotes fresh, broker offset, Supabase reachable, sync queue, disk, log size, internet latency, PC clock drift (per-minute).
  - Performance metrics: CPU, RAM, bar-processing latency, MT5 call latency p50/p95, queue sizes; WARNING above D4 budgets.
  - Debug bundle: zip of recent logs + crash reports + masked settings + health + versions + last N decision traces + `README_DEBUG.md` with an AI prompt "Find the root cause of this problem."
  - Logs page UI: category tabs, live tail, filters (level/category/symbol/strategy/time/regex), JSON detail, full trace view, change level at runtime, debug-mode toggle (auto-revert), export, open folder.
  - Health page UI: checks, performance metrics, worker status, debug bundle button.

## [0.1.0] - 2025-01-01

### Added
- Initial release — Phase 1 Foundation.
