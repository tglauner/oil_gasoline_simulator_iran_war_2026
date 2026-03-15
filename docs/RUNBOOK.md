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
- Detailed backend diagnostics are written to `backend/logs/app.log`
- The log file is truncated on each backend startup so it does not grow without bound
- Each API response includes `X-Request-ID`, which can be matched against the backend log
- Parse failures log which expected fields were found and a compact snippet of the EIA section that failed
- For deep analysis, set `LOG_LEVEL=DEBUG` in `backend/.env` and restart the backend
- If EIA history endpoints are slow, raise `SOURCE_FETCH_TIMEOUT_SECONDS` in `backend/.env` above the default `40`
- Keep `EXPOSE_INTERNAL_ERROR_DETAILS=false` unless you explicitly want 500 response bodies to include internal exception text during local debugging

### Build or install fails

- Ensure you are using Node 20+ and Python 3.13+
- Delete `frontend/node_modules` and rerun `npm ci` if frontend deps are corrupted
- Recreate `backend/.venv` if the backend environment is inconsistent
