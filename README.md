# oil_gasoline_simulator_iran_war_2026

React/Vite frontend plus FastAPI backend for:

- current WTI crude pricing
- current U.S. gasoline pricing
- a trip and fill-up calculator
- a weekly crude-to-gasoline simulation model based on EIA historical data

## Repo layout

- `frontend/` React + Vite UI
- `backend/` FastAPI API and modeling logic
- `infra/` Apache and systemd templates
- `docs/` runbook and deviations
- `scripts/` local bootstrap helper
- `.github/` CI workflow

## Local development

### 1. Bootstrap

```bash
cd /Users/tglauner/Library/CloudStorage/Dropbox/2\ -\ TG\ Investments\ and\ Research/Projects/oil_gasoline_simulator_iran_war_2026
sh scripts/bootstrap_local.sh
```

### 2. Start the backend

```bash
cd /Users/tglauner/Library/CloudStorage/Dropbox/2\ -\ TG\ Investments\ and\ Research/Projects/oil_gasoline_simulator_iran_war_2026/backend
. .venv/bin/activate
uvicorn app.main:app --reload
```

### 3. Start the frontend

```bash
cd /Users/tglauner/Library/CloudStorage/Dropbox/2\ -\ TG\ Investments\ and\ Research/Projects/oil_gasoline_simulator_iran_war_2026/frontend
npm ci
npm run dev
```

Frontend default URL: `http://127.0.0.1:5173`

Backend default URL: `http://127.0.0.1:8000`

## Validation

Frontend build:

```bash
cd frontend
npm run build
```

Backend tests:

```bash
cd backend
. .venv/bin/activate
pytest
```

## Environment files

- `frontend/.env.example`
- `backend/.env.example`
- `IRAN_WAR_START_DATE` defaults to `2026-02-28` and controls the vertical event marker on the 104-week oil and gasoline charts

## Debug logging

- Backend runtime logs go to `backend/logs/app.log`
- The backend truncates that log file on each startup when `TRUNCATE_LOGS_ON_STARTUP=true`
- Request logs include request IDs, response status, client host, and duration
- EIA source diagnostics include fetch timing, source URL, error class, and fallback reason
- Parse failures log field-level booleans and a compact section snippet so EIA markup changes can be diagnosed quickly
- The frontend exposes source diagnostics in the warning panel when fallback or hybrid mode is active
- Set `LOG_LEVEL=DEBUG` in `backend/.env` when you want header-level fetch diagnostics in the terminal and log file
- `SOURCE_FETCH_TIMEOUT_SECONDS` defaults to `40` to tolerate slower EIA responses; raise it in `backend/.env` if their history pages are especially slow
- Leave `EXPOSE_INTERNAL_ERROR_DETAILS=false` in production so 500 responses stay sanitized while full details remain in logs

## Data sources

- EIA daily prices page for current WTI and AAA retail gasoline
- EIA weekly gasoline history for the simulation series
- EIA WTI history for the crude factor
- NBER gasoline asymmetry paper for the model shape

## Notes

- The backend falls back to deterministic synthetic data if live EIA fetches fail.
- The app is read-only for now, so there is no DB, auth, or billing integration yet.
- Frontend lockfile is committed, so local setup and CI should use `npm ci`.
- See `docs/DEVIATIONS.md` for the temporary differences from the full app architecture standard.
