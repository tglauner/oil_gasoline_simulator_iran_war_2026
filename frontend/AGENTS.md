# AGENTS.md (frontend)

## Stack
- React app created for Vite
- Keep API calls centralized in the main app or a small helper
- Prefer plain CSS over adding a UI framework

## Local dev
- Install dependencies with `npm install` until `package-lock.json` exists, then switch to `npm ci`
- Run with `npm run dev`
- Verify the production bundle with `npm run build`

## Conventions
- Keep the UI local-first and explicit about live-data versus fallback-data mode.
- Avoid adding heavy charting libraries unless the current SVG approach is insufficient.
