# Security Policy

> This document describes how the MT5 Trading Workstation handles secrets and how to report vulnerabilities. It implements `docs/SPEC.md` Part D5.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x (Phase 1) | ✅ Active development — security fixes on `main` |

## Secret Handling

### MT5 Account Credentials

- Credentials (login, password, server) are **never stored in code, config files, `.env`, or SQLite**.
- They are stored only in **Windows Credential Manager** via the `keyring` library (`keyring==25.4.1`).
- The app reads them at runtime via `keyring.get_password(service, username)` and holds them in memory as `pydantic.SecretStr`.
- On logout or credential rotation, the entry is deleted via `keyring.delete_password`.

### Supabase

- The app uses the **Supabase `anon` key only**. The `service_role` key is never bundled, never stored on the client, and never committed.
- Row Level Security (RLS) enforces per-user access. The client cannot bypass RLS.
- Supabase URL and anon key are treated as config (not secrets) but are still not logged.

### LLM Calls (Future Phases)

- LLM calls **never include** MT5 passwords, Supabase keys, or full account numbers.
- Account `login` is optional and only sent if the user explicitly enables an LLM feature that needs it; otherwise a pseudonymous `account_id` is used.
- Prompts and completions are logged only as hashes/lengths, never verbatim with secrets.

### Logging, Exports, and Debug Bundles

- All sinks via `loguru` apply a redaction filter: `password`, `passwd`, `secret`, `token`, `key`, `authorization` values are replaced with `***REDACTED***`.
- Trade exports (CSV/JSON) and debug bundles strip credentials and mask account logins (e.g., `123****`).
- `crash_reports/` never includes memory dumps with secrets.

### Local Data

- SQLite databases (`*.db`) contain trades/bars/journal but **no passwords**.
- `.env` and `.env.local` are git-ignored and must never be committed.
- Pre-commit hook `check-added-large-files` blocks accidental commits of `.db` or model files.

## Reporting a Vulnerability

If you discover a security vulnerability, please do **not** open a public issue.

1. Email: **security@mt5-workstation.example.com** (placeholder — replace with real contact before public release)
2. Include: affected version, steps to reproduce, impact, and any PoC (without real credentials).
3. You will receive an acknowledgement within **3 business days**.

We follow a **90-day disclosure** policy: after you report, we will fix and release within 90 days, then you may disclose. We will credit you in `CHANGELOG.md` unless you prefer to remain anonymous.

## Hardening Roadmap

- Phase 13: Signed installer and update signature verification (Part J)
- Phase 14: Full credential audit, single-instance mutex, and secret-scan CI
- Ongoing: `ruff` rule `S` (bandit) and `mypy` strict checks

*For architecture details, see `docs/ARCHITECTURE.md` and `docs/SPEC.md` Part D5.*
