## Summary
<!-- Briefly describe what this PR does and why. Link related issues: Closes #... -->

## Phase
<!-- e.g., Phase 1 — Scaffolding / Phase 2 — ... -->
- Phase: 
- Spec section: [`docs/SPEC.md`](docs/SPEC.md)
- Progress tracker: [`docs/PROGRESS.md`](docs/PROGRESS.md)

## What was built
<!-- List files/modules created or modified -->
- 
- 
- 

## How to test
<!-- Commands and manual steps to verify the change -->
```pwsh
pip install -e ".[dev]"
ruff check .
ruff format --check .
mypy app
pytest
python -m app.main --self-check
```

## Acceptance checklist
<!-- Phase 1 checklist — check all that apply, or mark N/A with reason -->
<!-- See docs/SPEC.md#part-g for full acceptance criteria -->
- [ ] Project scaffolding complete (`pyproject.toml`, `app/__version__.py`, `app/main.py`, `README.md`)
- [ ] `pip install -e ".[dev]"` succeeds on Windows 10/11 with Python 3.11 x64
- [ ] `ruff check .` passes with no errors
- [ ] `ruff format --check .` passes
- [ ] `mypy app` passes with no errors
- [ ] `pytest` passes (FakeMT5 used — no real MT5 required in CI)
- [ ] `python -m app.main --self-check` exits 0 (MetaTrader5 import check)
- [ ] GitHub workflows present and valid (ci.yml, build.yml, release-please.yml, release.yml, codeql.yml)
- [ ] Issue/PR templates and Dependabot config present
- [ ] Documentation updated (`docs/SPEC.md`, `docs/PROGRESS.md` if needed)

## Known limitations
<!-- List anything intentionally deferred or stubbed for later phases -->
- `scripts/build.py` wraps PyInstaller CLI; `scripts/build.spec` will be added in a later phase
- `scripts/installer.iss` (Inno Setup) will be created in Release phase (G3 phase 16) — `release.yml` will fail loudly until then
- 

## Screenshots
<!-- Add screenshots/GIFs for UI changes, if applicable -->
<!-- Drag & drop images here -->

## Test on your PC (Part I6 steps)
<!-- Follow docs/SPEC.md Part I §6 — Manual smoke test on Windows -->
1. Clone this branch: `git checkout <branch>`
2. Create venv with Python 3.11 x64: `py -3.11 -m venv .venv && .\.venv\Scripts\Activate.ps1`
3. Install: `pip install --no-cache-dir -e ".[dev]"`
4. Lint/type/test: `ruff check . && ruff format --check . && mypy app && pytest`
5. Self-check: `python -m app.main --self-check` (or `dist\MT5TradingWorkstation\MT5TradingWorkstation.exe --self-check` after build)
6. Build (optional): `python scripts/build.py` then run the exe and verify Health page → Create debug bundle
7. Report OS / Python / MT5 build in comments

---
> **Note:** Keep PRs small and focused on a single phase. Link the phase task issue and ensure CI is green before requesting review.
