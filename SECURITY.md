# Security policy

This dashboard sits between a customer and your Checkmk instance. It holds an
automation secret for Checkmk and shows what Checkmk says is broken, so the
things that matter are: the secret staying on the server, the dashboard showing
only the site it was configured for, and nothing a viewer does reaching
Checkmk. A flaw in any of them can show one customer's monitoring to someone
else, so please report it privately.

## Reporting a vulnerability

Use GitHub's **private vulnerability reporting** on this repository
(Security › Report a vulnerability). Do not open a public issue or pull request
for a security problem.

Please include the commit you ran, how you deployed it (container or systemd,
which reverse proxy, whether `DASHBOARD_USER`/`DASHBOARD_PASSWORD` and
`CMK_SITE` were set), the Checkmk version, and the smallest request or
configuration that shows the problem. Say what an attacker needs to start with:
network access to the dashboard, the dashboard password, or control over a
monitored host's check output.

This is a one-person project. Reports are read and answered as soon as
possible, with no promised response time. Reporters are credited in the fix or
advisory unless they prefer otherwise.

## Supported versions

This repository has no releases or tags and is run straight from the
repository. Only `main` receives fixes; there is nothing older to patch, so
update by pulling `main` and rebuilding or restarting.

## How it works, as far as security goes

Everything below can be checked in `main.py` and `checkmk.py`.

- **The Checkmk credential** is `CMK_USER` and `CMK_SECRET`, read from the
  environment when the process starts. In practice that is a `.env` file loaded
  by python-dotenv, `--env-file` for a container, or `EnvironmentFile=` for
  systemd; the deployment guide keeps the file outside the image and at mode
  600. It is sent as an `Authorization: Bearer` header on every request to
  Checkmk. No endpoint returns it (`/api/config` returns only the title, the
  site name, the support contacts and the logo path), and the application never
  logs the header. The error log does contain Checkmk's response body
  and the exception text, which includes the request URL, so keep credentials
  out of `CMK_URL`. The browser gets a fixed "Could not connect to Checkmk."
  on failure, never the exception.
- **The site filter** is a single value, `CMK_SITE`, set by the operator. It is
  sent to Checkmk as the `sites` query parameter on the one request the
  application makes, so Checkmk does the filtering. The response is not checked
  afterwards, and the request does not ask for the site column, so the
  application could not check it if it wanted to. Two things follow. If
  `CMK_SITE` is empty or unset, the parameter is left out and the dashboard
  shows everything the automation user can see. And the filter is only as
  good as Checkmk's handling of that parameter. Viewers cannot change it; no
  viewer input is forwarded to Checkmk.
- **Authentication** is optional HTTP basic auth, one shared username and
  password for everyone, active only when both `DASHBOARD_USER` and
  `DASHBOARD_PASSWORD` are set. With either empty the dashboard is open. It
  covers `/`, `/api/config` and `/api/problems`, not `/static/` (the page
  shell, vendored CSS and your logo). There is no TLS, rate limiting or lockout
  in the application: those come from the reverse proxy you put in front of it.
  The deployment guide binds the dashboard to `127.0.0.1` for that reason; the
  Dockerfile listens on `0.0.0.0` inside the container, so what is reachable is
  decided by your port mapping.
- **Read-only** here means one thing: the application makes a single `GET` to
  `/check_mk/api/1.0/domain-types/service/collections/all` and no other
  outbound call. Whether the Checkmk account can also write is decided in
  Checkmk by the role you gave it, not by this code.
- **TLS to Checkmk** is not verified by default. Set `CMK_TLS_VERIFY=true` or
  point `CMK_CA_BUNDLE` at your CA. Until you do, the automation secret goes
  to a server whose identity is not checked.
- **The page** escapes host names, service names, plugin output and
  acknowledgement comments before putting them in the DOM. Those fields come
  from monitored hosts and Checkmk users, not from the dashboard's viewers.

## What an operator can get wrong

This is the paragraph to read before putting a customer in front of it. Any of
these shows a customer more than they should, and none is a vulnerability in
the code:

- **Leaving `CMK_SITE` empty** on an instance that serves a customer. The
  filter is then off. The `.env.example` value is the placeholder `sitename`,
  which has to be replaced by your real site name.
- **Pointing several customers at one site.** The filter is per site, not per
  customer, host or folder. Anyone who can open an instance sees every problem
  on that site. For several customers on one site, run one instance per
  customer with an automation user that Checkmk itself restricts (contact
  groups); the dashboard cannot do that separation for you.
- **Giving the automation user a role that sees everything.** The deployment
  guide suggests the Guest role, and Checkmk describes Guest as a role that may
  see everything. The dashboard can only show what that user is allowed to see,
  so the site filter is the only narrowing left. If you want a second layer,
  use a user limited by contact groups in Checkmk.
- **Setting only one of `DASHBOARD_USER` and `DASHBOARD_PASSWORD`**, or copying
  `.env.example` and leaving its example password in place. The first disables
  authentication without a warning; the second means everyone who has read
  this repository knows the password.
- **Publishing the port** (`-p 9000:9000`, or `--host 0.0.0.0` without a
  firewall) or serving it over plain HTTP. Basic auth is only as private as the
  connection it travels over.
- **Sharing one dashboard login** between customers. There is one credential;
  it identifies nobody.
- **Mounting anything sensitive under `static/`.** The directory is served
  without authentication.

## Scope

Treat these as vulnerabilities and report them:

- Getting data for a site other than `CMK_SITE` from a correctly configured
  instance, by any request.
- Any viewer-controlled value (path, query string, header, cookie) reaching the
  request to Checkmk, or changing which site is queried.
- Bypassing basic auth when both variables are set, or reaching `/api/*`
  without it.
- The Checkmk secret or the dashboard password appearing in a response, a log
  line, an error page or the container image.
- Script execution in a viewer's browser through any field that comes from
  Checkmk.
- Any way to make the application write to Checkmk, or call anything other than
  the one endpoint above.
- A dependency flaw in `requirements.txt` that is reachable in this application.

These are expected behaviour or the operator's responsibility, not
vulnerabilities:

- No per-customer isolation inside a site, one shared password, no user
  accounts, no audit log. The README says so.
- Everything under "What an operator can get wrong".
- An instance exposed to the internet without a reverse proxy, TLS and
  authentication in front of it.
- TLS verification being off by default. A way around it while it is turned on
  is in scope.
- Request volume. Each page view polls every 30 seconds and every poll becomes
  one request to Checkmk; there is no cache and no rate limiting here.
- Flaws in Checkmk itself, in nginx, or in your container runtime. Report those
  upstream.
- Findings that need control of the host, the `.env` file or the container.
