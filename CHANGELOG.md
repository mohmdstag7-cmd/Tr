# Changelog

All notable changes to the MT5 Trading Workstation will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Phase 1 foundation: repository scaffolding, pinned tooling, and GitHub workflows (CI on Windows for lint/type/test)
- Design tokens → QSS pipeline and base theme
- Main window shell (PySide6) with sidebar navigation, empty pages for all 16 phases, and command palette (Ctrl+K)
- Documentation: `docs/SPEC.md` reference, `docs/ARCHITECTURE.md` (ADRs), `docs/PROGRESS.md`, `README.md`, `AGENTS.md`, `SECURITY.md`
- Project metadata: `pyproject.toml` (pinned dependencies, ruff/mypy/pytest/coverage config), `.pre-commit-config.yaml`, `.editorconfig`, `.gitignore`, `LICENSE` (proprietary), `app/__version__.py`

[Unreleased]: https://github.com/your-org/mt5-trading-workstation/compare/v0.1.0...HEAD
