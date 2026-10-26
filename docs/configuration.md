# Configuration reference

All configuration is done through environment variables, typically via a `.env` file.
Copy [`.env.example`](../.env.example) as a starting point — it lists every option with inline
explanations.

For where the `.env` file lives and how to secure it, see the
[deployment guide](deployment.md#step-4--configuration).

---

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `CMK_URL` | Yes | — | Base URL of your Checkmk site, no trailing slash (e.g. `https://checkmk.example.com/mysite`) |
| `CMK_USER` | Yes | — | Username of the Checkmk automation user |
| `CMK_SECRET` | Yes | — | Automation secret of that user |
| `CMK_SITE` | No | *(all sites)* | Site name to filter on; empty shows all sites (see [site filtering](#filtering-by-site-distributed-monitoring)) |
| `TICKET_PATTERN` | No | `INC` | Ticket prefix used to detect ticket numbers in acknowledgement comments (see [ticket filtering](#ticket-filtering)) |
| `DASHBOARD_TITLE` | No | `Monitoring Dashboard` | Title shown in the navbar and browser tab |
| `DASHBOARD_LOGO` | No | *(default icon)* | Filename of a logo in `static/` (e.g. `logo.svg`); empty uses the built-in icon (see [company logo](#adding-a-company-logo)) |
| `DASHBOARD_USER` | No | *(auth off)* | Username for HTTP basic auth; auth is disabled while this or `DASHBOARD_PASSWORD` is empty |
| `DASHBOARD_PASSWORD` | No | *(auth off)* | Password for HTTP basic auth |
| `SUPPORT_EMAIL` | No | *(hidden)* | Support email shown in the footer |
| `SUPPORT_PHONE` | No | *(hidden)* | Support phone number shown in the footer |
| `CMK_TLS_VERIFY` | No | `false` | Set to `true` to verify the Checkmk server's TLS certificate (off by default for internal self-signed setups) |
| `CMK_CA_BUNDLE` | No | — | Path to a CA bundle file to verify against; takes precedence over `CMK_TLS_VERIFY` |

> **TLS note:** certificate verification is disabled by default because this dashboard typically
> targets internal Checkmk instances with self-signed certificates. Set `CMK_TLS_VERIFY=true`, or
> point `CMK_CA_BUNDLE` at your CA bundle, to enable it.

---

## Ticket filtering

### Alert categorisation

Every non-OK service is placed in one of three categories:

| Category | Condition |
|---|---|
| **Critical** | State = CRIT (2), not acknowledged with a ticket |
| **Warning** | State = WARN (1) or UNKNOWN (3), not acknowledged with a ticket |
| **Acknowledged** | Acknowledged **and** the comment contains `TICKET_PATTERN` |

A service only appears under **Acknowledged** if it has both an acknowledgement *and* a comment
containing a ticket number matching the configured `TICKET_PATTERN`.

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

```env
TICKET_PATTERN=INC     # matches INC-1234
TICKET_PATTERN=KT1     # matches KT1-5542
TICKET_PATTERN=TICKET  # matches TICKET-42
```

The check is case-insensitive.

---

## Filtering by site (distributed monitoring)

If you run Checkmk in distributed monitoring mode, set `CMK_SITE` to show alerts from only that
site. Alerts from connected remote sites are filtered out.

Leave `CMK_SITE` empty to show alerts from all sites.

---

## Adding a company logo

Set `DASHBOARD_LOGO` in `.env` to the filename of your logo and place the file in the `static/`
directory. The logo replaces the default activity icon in the navbar.

### Logo requirements

| | |
|---|---|
| **Format** | SVG (preferred) or PNG with transparent background |
| **Height** | 40 px display size; export PNG at 80 px or higher for retina screens |
| **Width** | Keep under 200 px to avoid crowding the navbar title |
| **Background** | Transparent — the navbar background is dark (`#1a1d27`) |

### Native install

Copy the logo into `static/` and set the filename in `.env`:

```bash
cp /path/to/yourlogo.svg /opt/checkmk-client-dashboard/static/yourlogo.svg
```

```env
DASHBOARD_LOGO=yourlogo.svg
```

Then restart the service:

```bash
sudo systemctl restart checkmk-client-dashboard
```

### Container (Podman / Docker)

Mount the logo into the container's `static/` directory at runtime:

```bash
podman run -d \
  --name checkmk-dashboard \
  --env-file /opt/checkmk-client-dashboard/.env \
  --restart unless-stopped \
  -p 127.0.0.1:9000:9000 \
  -v /opt/checkmk-client-dashboard/yourlogo.svg:/app/static/yourlogo.svg:ro \
  checkmk-dashboard
```

```env
DASHBOARD_LOGO=yourlogo.svg
```

The `:ro` flag mounts the file read-only. Place the logo anywhere on the host and adjust the
source path accordingly.

---

## Security

### Basic auth

Set `DASHBOARD_USER` and `DASHBOARD_PASSWORD` to protect the dashboard with HTTP Basic
Authentication. While either variable is empty, the page is accessible without a password.

> Basic auth is all-or-nothing: anyone who authenticates sees every problem for the configured
> site. It is not a per-customer access boundary. Do not expose this dashboard to the public
> internet (just as you would not do with Checkmk itself).

### Checkmk — read-only access

The application cannot manipulate the Checkmk environment:

- Only **read-only GET requests** are made to the Checkmk REST API
- **No user input** is forwarded to Checkmk — all query parameters are hardcoded in the source
- Checkmk credentials are stored only in `.env` on the server and are **never** sent to the browser
- FastAPI docs and OpenAPI spec are **disabled** (`/docs`, `/redoc` and `/openapi.json` are unavailable)

The automation user in Checkmk has the **Guest** role (read-only), so no write permissions are
granted from the Checkmk side either.
