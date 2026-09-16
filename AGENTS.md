# AGENTS.md (Repo Root) — TGIR App Architecture Standard

## Mission
Build small, consistent web apps with:
- Frontend: React (Vite)
- Backend: FastAPI (Python)
- DB: SQLite for MVP/local, PostgreSQL (Neon) for production
- Auth: Clerk
- Payments: Stripe (production)
- Hosting: DigitalOcean droplet (single server), Apache reverse proxy, Uvicorn/ASGI
- Marketing: Brevo
- Scraping: Apify (only when needed)
- Document consistently and keep all info up to date for all changes
- Keep for each app the required system demon configs documented and also apache config for the app

Codex: follow these rules before making changes. Ask if a requirement conflicts.

## Current Deployment Status

**On hold as of 2026-09-17.** The DigitalOcean systemd service and public Apache routes are disabled; retain the source and deployment artifacts for a future restart.

## Cost Discipline (non-negotiable)
- Default to the cheapest viable approach.
- Prefer single-droplet architecture; no Kubernetes, no extra managed services unless explicitly requested.
- Avoid adding new paid vendors unless there is a clear ROI and no free/cheap alternative.
- Prefer boring dependencies. If adding a library, justify it briefly in the PR description.

## Repo Layout (standard)
- /frontend  React + Vite app
- /backend   FastAPI app
- /infra     Apache + systemd + deployment notes/templates
- /scripts   one-off utilities (keep small)
- /docs      docs only (no code)
- /.github   CI, PR template

## Local Dev (Mac default)
Frontend:
- cd frontend
- npm ci
- npm run dev
- npm run lint
- npm run test (if configured)

Backend:
- cd backend
- python -m venv .venv
- source .venv/bin/activate
- pip install -r requirements.txt
- uvicorn app.main:app --reload

## Production (DigitalOcean, when resumed)
- Apache terminates TLS and reverse-proxies to Uvicorn.
- Serve only on port 443 in Apache vhost (no port 80 vhost).
- Use systemd for the backend service.
- Keep secrets out of git; use env vars on the droplet.

## Quality Gates (do before finalizing)
- Frontend: build must pass: `npm run build`
- Backend: app imports and starts; run tests if present: `pytest`
- No secrets in repo; update .env.example if new env vars are required.
- Keep changes minimal and consistent with existing patterns.

## Style Rules
- Prefer small diffs. Do not refactor unrelated code.
- Match the code style already in the repo.
- Prefer explicit, readable code over clever abstractions.

## When uncertain
- If requirements are ambiguous, propose 1–2 options and pick the lowest-cost default.
