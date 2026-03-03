# Checkmk Client Dashboard

A lightweight read-only monitoring dashboard that fetches non-OK services via the Checkmk REST API and categorises them as **Critical**, **Warning** or **Acknowledged**. The page auto-refreshes every 30 seconds.

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
sudo mkdir /opt/checkmk-client-dashboard
sudo chown checkmk-client-dashboard:checkmk-client-dashboard /opt/checkmk-client-dashboard

# Copy the project files
sudo cp -r . /opt/checkmk-client-dashboard/

# Install dependencies as the service user
sudo -u checkmk-client-dashboard python3 -m venv /opt/checkmk-client-dashboard/venv
sudo -u checkmk-client-dashboard /opt/checkmk-client-dashboard/venv/bin/pip install -r /opt/checkmk-client-dashboard/requirements.txt
```

---

## Step 4 — Configuration

```bash
sudo nano /opt/checkmk-client-dashboard/.env
sudo chown checkmk-client-dashboard:checkmk-client-dashboard /opt/checkmk-client-dashboard/.env
sudo chmod 600 /opt/checkmk-client-dashboard/.env
```

Contents of `.env`:

```env
# URL of your Checkmk site (no trailing slash)
CMK_URL=https://checkmk.yourcompany.com/sitename

# Automation user credentials
CMK_USER=dashboard
CMK_SECRET=your-automation-secret-here

# Site name — shown in the navbar and used as a filter so only alerts
# from this site appear (remote sites in distributed monitoring are excluded)
CMK_SITE=sitename

# Title shown in the browser tab and navbar
DASHBOARD_TITLE=Monitoring Dashboard

# Prefix of ticket numbers in acknowledge comments (default: INC)
TICKET_PATTERN=INC

# Basic auth for the dashboard (optional but strongly recommended)
# Leave empty to disable auth
DASHBOARD_USER=admin
DASHBOARD_PASSWORD=choose-a-strong-password
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
| `DASHBOARD_USER` | No | Username for basic auth; empty = no auth |
| `DASHBOARD_PASSWORD` | No | Password for basic auth; empty = no auth |

---

## Step 5 — Systemd service

```bash
sudo nano /etc/systemd/system/checkmk-client-dashboard.service
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
ExecStart=/opt/checkmk-client-dashboard/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
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
