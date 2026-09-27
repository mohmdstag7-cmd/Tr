# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-09-27

### Added
- **Phase 2 — Observability**: structured JSON logging via loguru with 17 categories, trace IDs, secrets masking, crash handler, watchdog, audit log, 10 health checks, performance metrics, debug bundle creator. Logs page + Health page UI.
- **Phase 3 — MT5 Connection**: real `MT5Gateway` (single-threaded owner of all MT5 calls via command queue), `FakeMT5` simulator for CI, first-run connection wizard, account profiles (keyring), symbol cache + suffix mapping, market data store with sanity checks, history sync, connection diagnostics page, `mt5_smoke_test` script + `--mt5-smoke-test` CLI flag.

### Fixed
- **11 critical bugs** from the Phase 1-3 audit (cross-verified with Opus 5.5):
  - MT5Gateway now lazily constructed in MainWindow (was: never instantiated)
  - release.yml now runs real PyInstaller (was: shipped a 15-byte "dummy installer")
  - `_check_broker_offset_stable` no longer violates ADR-002 (was: direct MT5 call from main thread)
  - `audit_log.log()` signature fixed (was: TypeError on connection-lost event)
  - `SecretsMaskingFilter` now catches 11 more sensitive key names + inline `key=value` patterns
  - `_submit` no longer leaks `threading.Timer` per call + TOCTOU race fixed
  - `MT5Gateway.__del__` added with 100ms timeout (was: QThread destroyed on GC)
  - `AccountInfo.account_type` now correctly assigned (was: always "demo")
  - `HealthRegistry`/`metrics`/`watchdog` no longer start QTimers at module import (was: before QApplication)
  - `MainWindow.closeEvent` now tears down all singletons (was: just `event.accept()`)
  - `SingleInstance` lock now acquired with default profile (was: only with `--profile`)
- **5 medium bugs**: supabase/LLM settings fields added to AppSettings, audit log now redacts secrets, masking scrubs inline patterns, smoke test returns int exit code.

## [0.1.0] - 2025-01-01

### Added
- Initial release — Phase 1 Foundation.
