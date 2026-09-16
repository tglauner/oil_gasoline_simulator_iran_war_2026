# oil_gasoline_simulator_iran_war_2026

> **Status (2026-09-17): On hold.** The DigitalOcean production service and public routes have been disabled. The code remains available for a future restart.

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
uvicorn app.main:app --reload --port 8003
```

### 3. Start the frontend

```bash
cd /Users/tglauner/Library/CloudStorage/Dropbox/2\ -\ TG\ Investments\ and\ Research/Projects/oil_gasoline_simulator_iran_war_2026/frontend
npm ci
npm run dev
```

Frontend default URL: `http://127.0.0.1:5173`

Backend default URL: `http://127.0.0.1:8003`

During local development, the Vite dev server proxies `/api` and `/health` to the backend on `127.0.0.1:8003`, so `frontend/.env` is usually not needed unless you want a non-default API target.

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

## Production (on hold)

The DigitalOcean service and public Apache routes are disabled. The following deployment model is retained for a future restart.

Production target:
- `https://oil-gasoline-simulator-iran-war-2026.tglauner.com`

Deployment model:
- Existing Apache on the droplet serves `frontend/dist` from `/var/www/html/oil_gasoline_simulator_iran_war_2026/frontend/dist`
- Apache proxies `/api` and `/health` to the local uvicorn service
- Apache site files live under `/etc/apache2/sites-available`
- systemd runs the backend on `127.0.0.1:8003`

Use the Apache + systemd droplet runbook in `docs/RUNBOOK.md` for the exact deployment commands.

## Environment files

- `frontend/.env.example`
- `backend/.env.example`
- In production, the frontend can use same-origin API calls with no `VITE_API_BASE_URL` override
- `frontend/.env.example` is for local development; do not copy it into the droplet build unless you intentionally want a non-default API target
- `TRUMP_ADMINISTRATION_START_DATE` defaults to `2025-01-20` and controls the vertical marker for the second Trump administration on the 104-week oil and gasoline charts
- `IRAN_WAR_START_DATE` defaults to `2026-02-28` and controls the vertical event marker on the 104-week oil and gasoline charts

## Debug logging

- Backend runtime logs go to `backend/logs/app.log`
- Local-safe default behavior truncates that log file on startup when `TRUNCATE_LOGS_ON_STARTUP=true`
- The supplied production `.env` and `logrotate` setup keep the log growing safely over long uptime without wiping it on every restart
- Request logs include request IDs, response status, client host, and duration
- The production systemd unit disables Uvicorn access logs because Apache already records access traffic
- EIA source diagnostics include fetch timing, source URL, error class, and fallback reason
- Parse failures log field-level booleans and a compact section snippet so EIA markup changes can be diagnosed quickly
- The frontend exposes source diagnostics in the warning panel when fallback or hybrid mode is active
- Set `LOG_LEVEL=DEBUG` in `backend/.env` when you want header-level fetch diagnostics in the terminal and log file
- `SOURCE_FETCH_TIMEOUT_SECONDS` defaults to `40` to tolerate slower EIA responses; raise it in `backend/.env` if their history pages are especially slow
- Leave `EXPOSE_INTERNAL_ERROR_DETAILS=false` in production so 500 responses stay sanitized while full details remain in logs
- Apache access/error logs are separate and are normally already managed by Ubuntu's packaged `logrotate` rules

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
