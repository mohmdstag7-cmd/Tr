# AGENTS.md — Rules for AI Agents Working in This Repo

> These rules are mandatory for any AI assistant or agent contributing code. Violations block the PR.

## 1. Read First

Always read **`docs/SPEC.md`** (full spec) and **`docs/PROGRESS.md`** (current phase status) before writing any code. Do not assume — check Part A (work rules), D2/D3 (architecture), G3 (acceptance), H (GitHub files), I (packaging), J (auto-update).

## 2. Branching & PRs

- Work in branches named `phase/NN-name` (e.g., `phase/01-foundation`, `phase/02-observability`).
- PR into `main`. **Never push directly to `main`.**
- Keep PRs small and focused on one phase/batch.
- Use **Conventional Commits**: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`.

## 3. Hard Constraints (SPEC Part G4 — Never Violate)

These are non-negotiable. Any PR violating them will be rejected:

- **Paper-by-default** — no live trading without explicit user confirmation.
- **Server-side SL on every live order** — never place a live order without a stop-loss.
- **No martingale / grid / averaging** — forbidden strategies.
- **No look-ahead** — closed-bar only; never use future data.
- **Secrets never in code / logs / exports / LLM prompts** — credentials via Windows Credential Manager (`keyring`) only; mask in logs.
- **Shipped app uses only real MT5** — `FakeMT5` is allowed **only in `tests/`**.

## 4. Architecture Rules (SPEC Part D3)

- **MT5Gateway single thread** — all `MetaTrader5` calls go through `app/mt5/gateway.py` on its dedicated thread. UI never imports `MetaTrader5` directly.
- **UI never blocks** — no synchronous MT5 or I/O on the main (Qt) thread; use signals/workers.
- **Closed-bar driven** — strategies receive only closed bars.
- **One Broker interface** — `app/broker/interface.py` for live/paper/backtest.
- **Domain purity** — `app/domain/` has no Qt/MT5/IO imports.
- **Idempotency & crash safety** — operations must be retry-safe; SQLite is source of truth.
- **Single instance** — app enforces a Win32 mutex.
- **Config safety** — Pydantic v2 validation; `SecretStr` for secrets.

## 5. Commands

```powershell
# Lint
ruff check .
ruff format --check .

# Type check
mypy app

# Tests (requires Python 3.11)
pytest

# Run the app
python -m app.main
# or after install:
mt5-workstation
```

## 6. Before Pushing

- `ruff check` — must be clean
- `ruff format --check` — must be clean
- `mypy app` — must be clean (strict on `app/`)
- `pytest` — must be green (Windows)
- If CI fails, **fix on the same branch** — do not open a new PR.

## 7. Docs & Changelog

Every PR must update:

- `docs/PROGRESS.md` — move tasks, update phase table/narrative
- `CHANGELOG.md` — add entry under `## [Unreleased]`

Do not edit `docs/SPEC.md` without explicit approval.

## 8. Security

- Never log, print, or commit secrets, tokens, or account numbers.
- Use `keyring` (Windows Credential Manager) for MT5 credentials; Supabase uses `anon` key only.
- When in doubt, mask it.

*If a rule here conflicts with `docs/SPEC.md`, SPEC wins.*
