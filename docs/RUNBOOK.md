# RUNBOOK

## Local startup

1. Run `sh scripts/bootstrap_local.sh`
2. Start the backend from `backend/`
3. Start the frontend from `frontend/`

## Common checks

- Frontend build: `cd frontend && npm run build`
- Backend tests: `cd backend && . .venv/bin/activate && pytest`

## Production deployment

### Target

- Droplet hostname: `oil-gasoline-simulator-iran-war-2026.tglauner.com`
- Ubuntu release assumed: `24.04.x`
- Web server: Apache
- Apache is already installed and already serving other TG Launer sites
- Existing Apache site files live in `/etc/apache2/sites-available`
- Backend service: systemd unit running uvicorn on `127.0.0.1:8003`
- Frontend delivery: Apache serving `/var/www/html/oil_gasoline_simulator_iran_war_2026/frontend/dist`
- App root on the droplet: `/var/www/html/oil_gasoline_simulator_iran_war_2026`

### 1. DNS and firewall

- Point the `A` record for `oil-gasoline-simulator-iran-war-2026.tglauner.com` at the droplet IP.
- In the DigitalOcean firewall, allow inbound `22`, `80`, and `443`.

### 2. Verify Apache and install only missing runtime packages

```bash
sudo apachectl -S
sudo apachectl -M | egrep 'proxy|proxy_http|ssl|headers|rewrite'
sudo ss -ltnp | egrep '127.0.0.1:(8000|8001|8002|8003|9000)' || true
python3 --version
command -v certbot
command -v node
sudo apt-get update
sudo apt-get install -y python3-venv git curl
if ! command -v certbot >/dev/null 2>&1; then sudo apt-get install -y certbot python3-certbot-apache; fi
if ! command -v node >/dev/null 2>&1; then curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt-get install -y nodejs; fi
```

Port note:
- This app is configured for `127.0.0.1:8003`.
- Your pasted droplet port scan showed `8000`, `8001`, `8002`, and `9000` already in use and `8003` free.
- If `8003` is ever occupied on a future deploy, update both the systemd unit and the Apache `ProxyPass` targets to the same replacement port before enabling the app.

### 3. Fetch the app

```bash
sudo mkdir -p /var/www/html
cd /var/www/html
sudo git clone https://github.com/tglauner/oil_gasoline_simulator_iran_war_2026.git
sudo chown -R "$USER":"$USER" /var/www/html/oil_gasoline_simulator_iran_war_2026
cd /var/www/html/oil_gasoline_simulator_iran_war_2026
git rev-parse HEAD
```

### 4. Build the backend

```bash
cd /var/www/html/oil_gasoline_simulator_iran_war_2026/backend
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pytest
```

### 5. Build the frontend

```bash
cd /var/www/html/oil_gasoline_simulator_iran_war_2026/frontend
rm -f .env
npm ci
npm run build
```

Production note:
- The frontend now defaults to same-origin API calls, so `VITE_API_BASE_URL` can stay unset in production.
- Do not leave `frontend/.env` in place on the droplet unless you explicitly need a non-default build target.

### 6. Create the production backend env file

```bash
cat >/var/www/html/oil_gasoline_simulator_iran_war_2026/backend/.env <<'EOF'
CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173,https://oil-gasoline-simulator-iran-war-2026.tglauner.com
ALLOWED_HOSTS=127.0.0.1,localhost,testserver,oil-gasoline-simulator-iran-war-2026.tglauner.com
CACHE_TTL_SECONDS=1800
LOG_LEVEL=INFO
TRUNCATE_LOGS_ON_STARTUP=false
EXPOSE_SOURCE_DIAGNOSTICS=false
EXPOSE_INTERNAL_ERROR_DETAILS=false
SOURCE_FETCH_TIMEOUT_SECONDS=40
TRUMP_ADMINISTRATION_START_DATE=2025-01-20
IRAN_WAR_START_DATE=2026-02-28
EOF
```

### 7. Set filesystem permissions

```bash
sudo chmod -R a+rX /var/www/html/oil_gasoline_simulator_iran_war_2026
sudo install -d -o www-data -g www-data /var/www/html/oil_gasoline_simulator_iran_war_2026/backend/logs
sudo chown -R www-data:www-data /var/www/html/oil_gasoline_simulator_iran_war_2026/backend/logs
```

### 8. Install backend log rotation

```bash
sudo install -m 0644 /var/www/html/oil_gasoline_simulator_iran_war_2026/infra/logrotate/oil_gasoline_simulator_iran_war_2026 /etc/logrotate.d/oil_gasoline_simulator_iran_war_2026
sudo logrotate -d /etc/logrotate.d/oil_gasoline_simulator_iran_war_2026
```

Log rotation note:
- This rotates `backend/logs/app.log` weekly, compresses old logs, and keeps 52 rotations.
- Apache logs are handled separately by Ubuntu's existing Apache `logrotate` package rules.

### 9. Install the systemd service

```bash
sudo cp /var/www/html/oil_gasoline_simulator_iran_war_2026/infra/systemd/oil_gasoline_simulator_iran_war_2026.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now oil_gasoline_simulator_iran_war_2026
sudo systemctl status oil_gasoline_simulator_iran_war_2026 --no-pager
```

### 10. Issue the TLS certificate if the subdomain is new

```bash
sudo certbot certonly --apache -d oil-gasoline-simulator-iran-war-2026.tglauner.com
```

If the certificate already exists, verify it:

```bash
sudo ls -l /etc/letsencrypt/live/oil-gasoline-simulator-iran-war-2026.tglauner.com/
```

### 11. Install the Apache HTTPS site without disturbing existing sites

```bash
sudo a2enmod proxy proxy_http ssl headers rewrite
sudo cp /var/www/html/oil_gasoline_simulator_iran_war_2026/infra/apache/oil_gasoline_simulator_iran_war_2026.conf /etc/apache2/sites-available/
sudo a2ensite oil_gasoline_simulator_iran_war_2026
sudo apachectl configtest
sudo systemctl reload apache2
```

Optional:
- If you want this subdomain to match the rest of the server's `:80` redirect pattern, also enable the helper in `infra/apache/oil_gasoline_simulator_iran_war_2026_redirect.conf`.
- Do not disable `000-default`, `default-ssl`, `tglauner-ssl.conf`, or any other live site on this droplet during this deploy.

### 12. Optional port 80 redirect site

```bash
sudo cp /var/www/html/oil_gasoline_simulator_iran_war_2026/infra/apache/oil_gasoline_simulator_iran_war_2026_redirect.conf /etc/apache2/sites-available/
sudo a2ensite oil_gasoline_simulator_iran_war_2026_redirect
sudo apachectl configtest
sudo systemctl reload apache2
```

### 13. Final production checks

```bash
sudo apachectl -S | egrep 'oil-gasoline|tglauner'
curl -I https://oil-gasoline-simulator-iran-war-2026.tglauner.com/
curl https://oil-gasoline-simulator-iran-war-2026.tglauner.com/health
curl https://oil-gasoline-simulator-iran-war-2026.tglauner.com/api/dashboard | python3 -m json.tool | head -n 40
sudo systemctl status oil_gasoline_simulator_iran_war_2026 --no-pager
sudo logrotate -d /etc/logrotate.d/oil_gasoline_simulator_iran_war_2026
sudo tail -n 100 /var/www/html/oil_gasoline_simulator_iran_war_2026/backend/logs/app.log
sudo tail -n 100 /var/log/apache2/oil_gasoline_simulator_iran_war_2026_error.log
```

Expected results:
- `curl -I` returns `200` or `301` to `https`
- `/health` returns JSON with `"status": "ok"`
- `/api/dashboard` returns current price payload without a 500
- systemd service is `active (running)`
- Apache `configtest` says `Syntax OK`
- `logrotate -d` completes without errors for the app log rule

### 14. Upgrade procedure

```bash
cd /var/www/html/oil_gasoline_simulator_iran_war_2026
sudo git pull origin main
cd backend
. .venv/bin/activate
pip install -r requirements.txt
cd ../frontend
npm ci
npm run build
sudo systemctl restart oil_gasoline_simulator_iran_war_2026
sudo apachectl configtest
sudo systemctl reload apache2
```

## Troubleshooting

### Frontend shows API errors

- Confirm the backend is running on `http://127.0.0.1:8003`
- In local development, restart `npm run dev` after frontend config changes so the Vite `/api` proxy is active
- Local `npm run dev` proxies `/api` and `/health` to `http://127.0.0.1:8003` by default
- Check `frontend/.env` or `frontend/.env.example` for `VITE_API_BASE_URL`
- Open `http://127.0.0.1:8003/health`
- In production, verify the built frontend is using same-origin API calls and that Apache is proxying `/api` and `/health`
- If the droplet build was done with a leftover `frontend/.env`, delete it and rerun `npm run build`

### Backend shows fallback mode

- The EIA fetchers could not reach or parse the live pages.
- The UI warning banner will show which source failed.
- The simulator still works locally using deterministic fallback data.
- Detailed backend diagnostics are written to `backend/logs/app.log`
- In production, keep `TRUNCATE_LOGS_ON_STARTUP=false` and install the provided `logrotate` rule so logs persist across restarts without growing without bound
- Each API response includes `X-Request-ID`, which can be matched against the backend log
- Parse failures log which expected fields were found and a compact snippet of the EIA section that failed
- For deep analysis, set `LOG_LEVEL=DEBUG` in `backend/.env` and restart the backend
- If EIA history endpoints are slow, raise `SOURCE_FETCH_TIMEOUT_SECONDS` in `backend/.env` above the default `40`
- Keep `EXPOSE_INTERNAL_ERROR_DETAILS=false` unless you explicitly want 500 response bodies to include internal exception text during local debugging

### Build or install fails

- Ensure you are using Node 20+ and Python 3.13+
- Delete `frontend/node_modules` and rerun `npm ci` if frontend deps are corrupted
- Recreate `backend/.venv` if the backend environment is inconsistent
- Run `sudo apachectl configtest` after every Apache config change
- Run `sudo systemctl status oil_gasoline_simulator_iran_war_2026 --no-pager` after every deploy
- Do not disable unrelated Apache sites on this droplet while deploying this app
