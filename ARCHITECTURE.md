# ARCHITECTURE

## Components
- Browser (React/Vite)
- API (FastAPI/Uvicorn)
- Reverse proxy (Apache)
- Database (SQLite local, Neon Postgres prod)
- External: Clerk (auth), Stripe (payments), Brevo (email), Apify (scraping)

## Data Flow
Browser -> Apache (443) -> Uvicorn (localhost) -> DB
Browser -> Clerk (auth)
Backend -> Stripe/Brevo/Apify as needed
