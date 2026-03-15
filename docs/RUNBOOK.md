# RUNBOOK

## Local startup

1. Run `sh scripts/bootstrap_local.sh`
2. Start the backend from `backend/`
3. Start the frontend from `frontend/`

## Common checks

- Frontend build: `cd frontend && npm run build`
- Backend tests: `cd backend && . .venv/bin/activate && pytest`

## Troubleshooting

### Frontend shows API errors

- Confirm the backend is running on `http://127.0.0.1:8000`
- Check `frontend/.env` or `frontend/.env.example` for `VITE_API_BASE_URL`
- Open `http://127.0.0.1:8000/health`

### Backend shows fallback mode

- The EIA fetchers could not reach or parse the live pages.
- The UI warning banner will show which source failed.
- The simulator still works locally using deterministic fallback data.

### Build or install fails

- Ensure you are using Node 20+ and Python 3.13+
- Delete `frontend/node_modules` and rerun `npm ci` if frontend deps are corrupted
- Recreate `backend/.venv` if the backend environment is inconsistent
