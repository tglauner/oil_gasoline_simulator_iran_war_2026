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
npm install
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

## Data sources

- EIA daily prices page for current WTI and AAA retail gasoline
- EIA weekly gasoline history for the simulation series
- EIA WTI history for the crude factor
- NBER gasoline asymmetry paper for the model shape

## Notes

- The backend falls back to deterministic synthetic data if live EIA fetches fail.
- The app is read-only for now, so there is no DB, auth, or billing integration yet.
- Frontend uses `npm install` for now because this sandbox could not generate `package-lock.json`; switch to `npm ci` after the first online install creates the lockfile.
- See `docs/DEVIATIONS.md` for the temporary differences from the full app architecture standard.
