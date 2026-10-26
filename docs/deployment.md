# Deployment guide

How to install and run the Checkmk Client Dashboard in production. Two paths:

- **[Native install](#native-install-systemd--nginx)** — systemd + nginx (Linux only)
- **[Container](#container-podman--docker)** — Podman / Docker; build once, run anywhere, including air-gapped servers

For all configuration options (environment variables, logo, ticket filtering, site filtering,
security), see **[configuration.md](configuration.md)**.

---

## Requirements

- Python 3.12 or higher (tested on 3.14)
- A Checkmk instance with REST API access (works on the free **Raw** edition)
- An automation user in Checkmk (see [Step 2](#step-2--create-an-automation-user-in-checkmk))

---

## Native install (systemd + nginx)

### Step 1 — Create a Linux user

The application runs under a dedicated system user with no login shell. Create it first:

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin checkmk-client-dashboard
```

### Step 2 — Create an automation user in Checkmk

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

### Step 3 — Install

```bash
sudo git clone https://github.com/Timdebruijn/checkmk-dashboard.git /opt/checkmk-client-dashboard
sudo chown -R checkmk-client-dashboard:checkmk-client-dashboard /opt/checkmk-client-dashboard

# Install dependencies as the service user
sudo -u checkmk-client-dashboard python3 -m venv /opt/checkmk-client-dashboard/venv
sudo -u checkmk-client-dashboard /opt/checkmk-client-dashboard/venv/bin/pip install -r /opt/checkmk-client-dashboard/requirements.txt
```

#### Offline installation (no internet access)

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

> **Python version**: The machine you download on must run the same Python version and OS architecture as the target server. Wheel files (`.whl`) are platform-specific. Check with `python3 --version`.

### Step 4 — Configuration

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

All other options are optional — see the full reference in **[configuration.md](configuration.md)**.

After editing, lock down the file:

```bash
sudo chown checkmk-client-dashboard:checkmk-client-dashboard /opt/checkmk-client-dashboard/.env
sudo chmod 600 /opt/checkmk-client-dashboard/.env
```

### Step 5 — Systemd service

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

### Step 6 — Nginx reverse proxy

Configure nginx to forward traffic to the uvicorn process. The service binds to `127.0.0.1:8000` so it is not directly reachable from outside.

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

## Container (Podman / Docker)

The `Dockerfile` builds a self-contained image with all dependencies included. Podman and Docker use identical commands — just swap `podman` for `docker` or vice versa.

> **Podman** is the recommended option. It runs rootless by default and has no daemon.

### Step A — Create the config file on the server

The container reads its configuration from a `.env` file on the **host** (the server running the container). The file is passed in at runtime and is never baked into the image.

```bash
sudo mkdir -p /opt/checkmk-client-dashboard
sudo cp .env.example /opt/checkmk-client-dashboard/.env
sudo vim /opt/checkmk-client-dashboard/.env      # fill in your values
sudo chmod 600 /opt/checkmk-client-dashboard/.env
```

The `.env.example` file contains all available options with explanations (full reference in **[configuration.md](configuration.md)**).

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

## Updating

Pull the latest code and refresh dependencies — the exact steps depend on how you deployed.

### Native install

```bash
cd /opt/checkmk-client-dashboard
sudo -u checkmk-client-dashboard git pull
sudo -u checkmk-client-dashboard venv/bin/pip install --upgrade -r requirements.txt
sudo systemctl restart checkmk-client-dashboard
```

Offline server: regenerate the `packages/` directory on an internet-connected machine (see [Offline installation](#offline-installation-no-internet-access)), transfer it, then run the same `pip install` with `--upgrade --no-index --find-links=packages`.

### Container (Podman / Docker)

```bash
cd /path/to/checkmk-dashboard
git pull
podman build -t checkmk-dashboard .
podman restart checkmk-dashboard   # Quadlet: sudo systemctl restart checkmk-dashboard
```

Air-gapped server: rebuild and `podman save` the image on an internet-connected machine, transfer it, then `podman load` and restart (see [Air-gapped deployment](#air-gapped-deployment-no-internet-on-target-server)).

> Dependency versions are pinned in `requirements.txt`, so an update only changes what a commit actually bumped — `pip install --upgrade` will not pull in untested major versions on its own.
