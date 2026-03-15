# infra

This directory contains starter deployment artifacts for a single DigitalOcean droplet:

- `apache/` reverse proxy vhost template
- `systemd/` backend service template

These templates are now prefilled for:

- domain: `oil-gasoline-simulator-iran-war-2026.tglauner.com`
- app root: `/var/www/oil_gasoline_simulator_iran_war_2026`
- backend service user: `www-data`
- Apache bootstrap config: `infra/apache/oil_gasoline_simulator_iran_war_2026_bootstrap.conf`
- Apache final TLS config: `infra/apache/oil_gasoline_simulator_iran_war_2026.conf`

Before deploying, verify:

- Apache modules `proxy proxy_http ssl headers rewrite` are enabled
- the Let’s Encrypt certificate exists for the domain
- `/var/www/oil_gasoline_simulator_iran_war_2026/backend/logs` is writable by `www-data`
- use the bootstrap Apache config first on a fresh droplet, then swap to the TLS config after `certbot certonly --apache` succeeds
