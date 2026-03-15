# DEVIATIONS

The app follows the standard frontend/backend/infra layout, but these standard components are intentionally not implemented yet:

- Database: not needed yet because the app is currently read-only and sourced from external market data.
- Clerk auth: not needed yet because there is no user-specific state or admin panel.
- Stripe: not needed yet because there are no paid features.
- Brevo: not needed yet because the app does not send email.
- Apify: not needed yet because the app uses direct EIA data pages instead of third-party scraping workflows.
- Frontend lockfile is now committed, so standard `npm ci` workflow is restored.

If the app later adds user accounts, saved scenarios, subscriptions, or lead capture, these items should be revisited.
