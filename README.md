# Checkmk Client Dashboard

A lightweight read-only monitoring dashboard that fetches non-OK services via the Checkmk REST API and categorises them as **Critical**, **Warning** or **Acknowledged**. The page auto-refreshes every 30 seconds.

---

## Deployment options

- **[Steps 1–6](#step-1--create-a-linux-user)** — native install with systemd + nginx (Linux only)
- **[Container (Podman / Docker)](#container-podman--docker)** — build once, run anywhere; also works on air-gapped servers

---

## Requirements

- Python 3.10 or higher
- A Checkmk instance with REST API access
- An automation user in Checkmk (see below)

---

## Step 1 — Create a Linux user

The application runs under a dedicated system user with no login shell. Create it first:

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin checkmk-client-dashboard
```

---

## Step 2 — Create an automation user in Checkmk

The dashboard uses an *automation user* to query the REST API — an account without a password but with an automation secret.

1. In Checkmk go to **Setup → Users → Users**
2. Click **Add user**
3. Fill in:
   - **Username**: `dashboard` (or any name you prefer)
   - **Full name**: `Dashboard automation`
   - **Authentication**: select **Automation secret for machine accounts**
   - Copy the generated secret — you will need it later
4. Assign the role **Guest** (read-only is sufficient)
5. Click **Save** and activate via **Activate pending changes**

> The secret is visible on the user page under the **Identity** tab.

---

## Step 3 — Install

```bash
sudo git clone https://github.com/Timdebruijn/checkmk-dashboard.git /opt/checkmk-client-dashboard
sudo chown -R checkmk-client-dashboard:checkmk-client-dashboard /opt/checkmk-client-dashboard

# Install dependencies as the service user
sudo -u checkmk-client-dashboard python3 -m venv /opt/checkmk-client-dashboard/venv
sudo -u checkmk-client-dashboard /opt/checkmk-client-dashboard/venv/bin/pip install -r /opt/checkmk-client-dashboard/requirements.txt
```

---

## Step 3b — Offline installation (no internet access)

If the target server has no internet access, download the packages on a machine that *does* have internet and transfer them manually.

**On a machine with internet access** (same OS and Python version as the target):

```bash
pip download -r requirements.txt -d ./packages
```

This creates a `packages/` directory containing all `.whl` and `.tar.gz` files.

**Transfer to the target server**, for example via SCP:

```bash
scp -r packages/ requirements.txt user@target-server:/opt/checkmk-client-dashboard/
```

**On the target server**, install from the local directory:

```bash
sudo -u checkmk-client-dashboard python3 -m venv /opt/checkmk-client-dashboard/venv
sudo -u checkmk-client-dashboard /opt/checkmk-client-dashboard/venv/bin/pip install \
    --no-index \
    --find-links=/opt/checkmk-client-dashboard/packages \
    -r /opt/checkmk-client-dashboard/requirements.txt
```

> **Python version**: The machine you download on must run the same Python version and OS architecture as the target server. Wheel files (`.whl`) are platform-specific.
>
> You can check the Python version with: `python3 --version`

---

## Step 4 — Configuration

Copy `.env.example` as a starting point — it contains all available options with explanations:

```bash
sudo cp /opt/checkmk-client-dashboard/.env.example /opt/checkmk-client-dashboard/.env
sudo vim /opt/checkmk-client-dashboard/.env
```

Minimum required values:

```env
CMK_URL=https://checkmk.yourcompany.com/sitename
CMK_USER=dashboard
CMK_SECRET=your-automation-secret-here
```

All other options are optional. See the configuration reference below.

After editing, lock down the file:

```bash
sudo chown checkmk-client-dashboard:checkmk-client-dashboard /opt/checkmk-client-dashboard/.env
sudo chmod 600 /opt/checkmk-client-dashboard/.env
```

### All configuration options

| Variable | Required | Description |
|---|---|---|
| `CMK_URL` | Yes | Base URL of your Checkmk site, no trailing slash |
| `CMK_USER` | Yes | Username of the automation user |
| `CMK_SECRET` | Yes | Automation secret of the user |
| `CMK_SITE` | No | Site name for filtering; empty = show all sites |
| `DASHBOARD_TITLE` | No | Page title (default: `Monitoring Dashboard`) |
| `TICKET_PATTERN` | No | Ticket prefix (default: `INC`) |
| `DASHBOARD_LOGO` | No | Filename of the logo in `static/` (e.g. `logo.svg`); empty = default icon |
| `DASHBOARD_USER` | No | Username for basic auth; empty = no auth |
| `DASHBOARD_PASSWORD` | No | Password for basic auth; empty = no auth |
| `SUPPORT_EMAIL` | No | Support email shown in the footer; empty = hidden |
| `SUPPORT_PHONE` | No | Support phone number shown in the footer; empty = hidden |

---

## Step 5 — Systemd service

```bash
sudo vim /etc/systemd/system/checkmk-client-dashboard.service
```

```ini
[Unit]
Description=Checkmk Client Dashboard
After=network.target

[Service]
Type=simple
User=checkmk-client-dashboard
WorkingDirectory=/opt/checkmk-client-dashboard
EnvironmentFile=/opt/checkmk-client-dashboard/.env
ExecStart=/opt/checkmk-client-dashboard/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable checkmk-client-dashboard
sudo systemctl start checkmk-client-dashboard
sudo systemctl status checkmk-client-dashboard
```

View logs:

```bash
sudo journalctl -u checkmk-client-dashboard -f
```

---

## Step 6 — Nginx reverse proxy

Configure nginx to forward traffic to the uvicorn process. The service binds to `127.0.0.1:8000` so it is not directly reachable from outside.

Create a new site config:

```bash
sudo vim /etc/nginx/sites-available/checkmk-client-dashboard
```

**1. Add the rate limiting zone to `/etc/nginx/nginx.conf`** inside the existing `http {}` block:

```nginx
http {
    # ...existing config...

    # Rate limiting zone for the dashboard — 10 req/s per IP, burst of 20
    limit_req_zone $binary_remote_addr zone=dashboard:10m rate=10r/s;
}
```

- **`rate=10r/s`** — max 10 requests per second per IP address
- **`burst=20`** — allows a short burst up to 20 before nginx returns `429 Too Many Requests`
- **`nodelay`** — burst requests are served immediately rather than delayed

**2. Create the site config in `/etc/nginx/sites-available/checkmk-client-dashboard`:**

```nginx
server {
    listen 80;
    server_name dashboard.yourcompany.com;

    location / {
        limit_req zone=dashboard burst=20 nodelay;

        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site and reload nginx:

```bash
sudo ln -s /etc/nginx/sites-available/checkmk-client-dashboard /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

> **HTTPS**: Use [Certbot](https://certbot.eff.org/) to add a TLS certificate. Certbot will update the nginx config automatically.
>
> ```bash
> sudo certbot --nginx -d dashboard.yourcompany.com
> ```

---

## Security

### Basic auth

Set `DASHBOARD_USER` and `DASHBOARD_PASSWORD` to protect the dashboard with HTTP Basic Authentication. As long as either variable is empty, the page is accessible without a password.

> Do not expose this dashboard to the public internet (just as you would not do with Checkmk itself).

### Checkmk — read-only access

The application cannot manipulate the Checkmk environment:

- Only **read-only GET requests** are made to the Checkmk REST API
- **No user input** is forwarded to Checkmk — all query parameters are hardcoded in the source
- Checkmk credentials are stored only in `.env` on the server and are **never** sent to the browser
- FastAPI docs and OpenAPI spec are **disabled** (`/docs`, `/redoc` and `/openapi.json` are unavailable)

The automation user in Checkmk has the **Guest** role (read-only), so no write permissions are granted from the Checkmk side either.

---

## Adding a company logo

Set `DASHBOARD_LOGO` in `.env` to the filename of your logo. Place the file in the `static/` directory. The logo is shown in the navbar; the default activity icon is hidden when a logo is set.

### Logo requirements

| | |
|---|---|
| **Format** | SVG (preferred) or PNG with transparent background |
| **Height** | 40 px display size; export PNG at 80 px or higher for retina screens |
| **Width** | Keep under 200 px to avoid crowding the navbar title |
| **Background** | Transparent — the navbar background is dark (`#1a1d27`) |

### Native install

Copy the logo into the `static/` directory and set the filename in `.env`:

```bash
cp /path/to/yourlogo.svg /opt/checkmk-client-dashboard/static/yourlogo.svg
```

```env
DASHBOARD_LOGO=yourlogo.svg
```

Then restart the service to apply the change:

```bash
sudo systemctl restart checkmk-client-dashboard
```

### Container (Podman / Docker)

Mount the logo file into the container's `static/` directory at runtime:

```bash
podman run -d \
  --name checkmk-dashboard \
  --env-file /opt/checkmk-client-dashboard/.env \
  --restart unless-stopped \
  -p 127.0.0.1:9000:9000 \
  -v /opt/checkmk-client-dashboard/yourlogo.svg:/app/static/yourlogo.svg:ro \
  checkmk-dashboard
```

Set the matching filename in `/opt/checkmk-client-dashboard/.env`:

```env
DASHBOARD_LOGO=yourlogo.svg
```

The `:ro` flag mounts the file read-only. Place the logo anywhere on the host and adjust the source path accordingly.

---

## How does ticket filtering work?

### Alert categorisation

Every non-OK service is placed in one of three categories:

| Category | Condition |
|---|---|
| **Critical** | State = CRIT (2), not acknowledged with a ticket |
| **Warning** | State = WARN (1) or UNKNOWN (3), not acknowledged with a ticket |
| **Acknowledged** | Acknowledged and comment contains `TICKET_PATTERN` |

A service only appears under **Acknowledged** if it has both an acknowledgement *and* a comment containing a ticket number that starts with the configured `TICKET_PATTERN`.

### Pasting a full URL as a comment

When acknowledging a service in Checkmk you can paste a full ticket URL as the comment:

```
https://yourcompany.atlassian.net/browse/INC-1234
```

The dashboard automatically extracts only the ticket number and displays:

```
INC-1234
```

Supported input formats in the acknowledge comment:

```
INC-1234
https://helpdesk.yourcompany.com/browse/INC-1234
See ticket INC-1234 for more information
KT1-5542
https://proxymanagedservices.atlassian.net/browse/KT1-5542
```

### Changing TICKET_PATTERN

Examples:

```env
TICKET_PATTERN=INC     # matches INC-1234
TICKET_PATTERN=KT1     # matches KT1-5542
TICKET_PATTERN=TICKET  # matches TICKET-42
```

The check is case-insensitive.

---

## Filtering by site (distributed monitoring)

If you run Checkmk in distributed monitoring mode, the dashboard by default only shows alerts from the site configured in `CMK_SITE`. Alerts from connected remote sites are filtered out.

Leave `CMK_SITE` empty to show alerts from all sites.

---

## Running locally (development)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your values
uvicorn main:app --reload
```

Available at `http://localhost:8000`.

---

## Container (Podman / Docker)

The `Dockerfile` builds a self-contained image with all dependencies included. Podman and Docker use identical commands — just swap `podman` for `docker` or vice versa.

> **Podman** is the recommended option. It runs rootless by default and has no daemon.

### Step A — Create the config file on the server

The container reads its configuration from a `.env` file on the **host** (the server running the container). The file is passed in at runtime and is never baked into the image.

Create the config file in a permanent location:

```bash
sudo mkdir -p /opt/checkmk-client-dashboard
sudo cp .env.example /opt/checkmk-client-dashboard/.env
sudo vim /opt/checkmk-client-dashboard/.env      # fill in your values
sudo chmod 600 /opt/checkmk-client-dashboard/.env
```

The `.env.example` file contains all available options with explanations (see [Configuration](#step-4--configuration)).

### Step B — Build the image

On a machine with internet access, from the project directory:

```bash
podman build -t checkmk-dashboard .
# docker build -t checkmk-dashboard .
```

### Step C — Run the container

```bash
podman run -d \
  --name checkmk-dashboard \
  --env-file /opt/checkmk-client-dashboard/.env \
  --restart unless-stopped \
  -p 127.0.0.1:9000:9000 \
  checkmk-dashboard
```

The `--env-file` points to the config file created in Step A.
The `-p 127.0.0.1:9000:9000` binding keeps the port local so it is only reachable via the nginx reverse proxy (see [Step 6](#step-6--nginx-reverse-proxy)).

> **Port note:** The container listens on port **9000**, not 8000. When adapting the Step 6 nginx config for container use, change `proxy_pass http://127.0.0.1:8000;` to `proxy_pass http://127.0.0.1:9000;`.

### Step D — Auto-start on boot

**Podman (4.4+) — Quadlet (recommended)**

Quadlet lets systemd manage the container directly from a declarative `.container` file — no manual `podman run` command needed after this point.

Create the file:

```bash
sudo vim /etc/containers/systemd/checkmk-dashboard.container
```

```ini
[Unit]
Description=Checkmk Client Dashboard
After=network.target

[Container]
Image=checkmk-dashboard
EnvironmentFile=/opt/checkmk-client-dashboard/.env
PublishPort=127.0.0.1:9000:9000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now checkmk-dashboard
```

**Podman (older than 4.4)**

```bash
podman generate systemd --name checkmk-dashboard --files --new
sudo mv container-checkmk-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now container-checkmk-dashboard
```

**Docker** — the `--restart unless-stopped` flag in Step C is sufficient when the Docker daemon itself starts on boot.

### Air-gapped deployment (no internet on target server)

If the target server has no internet access, build and export the image on a machine that *does* have internet.

**On a machine with internet access:**

```bash
podman build -t checkmk-dashboard .
podman save checkmk-dashboard | gzip > checkmk-dashboard.tar.gz
```

**Transfer the archive and the config** to the target server:

```bash
scp checkmk-dashboard.tar.gz user@target-server:~
scp .env.example user@target-server:~   # you will fill this in on the server
```

**On the target server:**

```bash
# Load the image
podman load < checkmk-dashboard.tar.gz

# Create and fill in the config
sudo mkdir -p /opt/checkmk-client-dashboard
sudo cp .env.example /opt/checkmk-client-dashboard/.env
sudo vim /opt/checkmk-client-dashboard/.env
sudo chmod 600 /opt/checkmk-client-dashboard/.env

# Run the container
podman run -d \
  --name checkmk-dashboard \
  --env-file /opt/checkmk-client-dashboard/.env \
  --restart unless-stopped \
  -p 127.0.0.1:9000:9000 \
  checkmk-dashboard
```

> The `.tar.gz` archive contains everything — Python, all packages, and the application code. No internet access is needed on the target server.

### Useful commands

```bash
# View logs
podman logs -f checkmk-dashboard

# Stop / remove
podman stop checkmk-dashboard && podman rm checkmk-dashboard

# Rebuild and restart after a code change
podman build -t checkmk-dashboard . && podman restart checkmk-dashboard
```
