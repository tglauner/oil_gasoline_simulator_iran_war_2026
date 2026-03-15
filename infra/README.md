# infra

This directory contains starter deployment artifacts for a single DigitalOcean droplet with Apache already installed:

- `apache/` reverse proxy vhost template
- `logrotate/` backend log retention config
- `systemd/` backend service template

These templates are now prefilled for:

- domain: `oil-gasoline-simulator-iran-war-2026.tglauner.com`
- app root: `/var/www/html/oil_gasoline_simulator_iran_war_2026`
- backend service user: `www-data`
- Apache TLS site: `infra/apache/oil_gasoline_simulator_iran_war_2026.conf`
- Optional Apache redirect site: `infra/apache/oil_gasoline_simulator_iran_war_2026_redirect.conf`
- Backend logrotate rule: `infra/logrotate/oil_gasoline_simulator_iran_war_2026`

Before deploying, verify:

- Apache modules `proxy proxy_http ssl headers rewrite` are enabled
- the Let’s Encrypt certificate exists for the domain
- `/var/www/html/oil_gasoline_simulator_iran_war_2026/backend/logs` is writable by `www-data`
- the new site is added alongside existing TG Launer Apache sites, not by disabling them
- the backend logrotate rule is installed so `backend/logs/app.log` does not grow forever
