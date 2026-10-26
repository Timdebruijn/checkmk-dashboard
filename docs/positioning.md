# Checkmk Client Dashboard — Market & USP Inventory

> **Internal positioning & strategy notes** — background for the README and future messaging,
> not product documentation. Market snapshot taken 2026-10-26; competitor facts drift, so
> re-check before reusing.

Synthesis of three research tracks, each with web-sourced claims in `research/`:
[competitors](research/competitors.md), [demand & pain points](research/demand.md),
[Checkmk gaps & positioning](research/gaps-and-positioning.md).

Audience decision: **broad** (self-hosters + internal IT/NOC teams + MSPs), leading with the
MSP / client-facing angle as the sharpest hook.

---

## What the product is (one sentence)
A tiny, self-hosted, read-only web dashboard that sits in front of an existing Checkmk
instance and shows only the services that need attention — Critical, Warning, and
Acknowledged-with-a-ticket — on one clean, brandable, auto-refreshing screen, without ever
exposing the Checkmk UI or credentials to the viewer.

---

## USPs / differentiators (ranked by strength of evidence)

1. **Client-safe by construction.** Only read-only GET requests to Checkmk; no user input is
   ever forwarded; credentials live server-side and never reach the browser; Checkmk's API
   docs/OpenAPI are disabled; the Checkmk UI stays hidden. Every alternative requires
   deliberate RBAC or anonymous-access setup to get close — NagVis's documented TV auto-login
   even puts credentials in the URL. We are safe *by default*, not by configuration.

2. **Acknowledged + ticket = "someone's on it" (genuinely novel).** When an alert is
   acknowledged in Checkmk with a comment containing a ticket reference (plain `INC-1234`, a
   full Jira/helpdesk URL, configurable prefix, case-insensitive), the dashboard extracts the
   ticket number and surfaces it as an at-a-glance triage signal. Checkmk has **no** native
   per-alert ticket tracking; the community explicitly proposed this exact approach. Jira
   number surfacing is commercial-only and very recent. This axis is ours alone.

3. **Curated "problems only" view.** Non-OK services in three fixed buckets
   (Critical / Warning / Acknowledged). Matches the NOC "only show failures; empty = healthy"
   design pattern. Far simpler than Checkmk's own UI (Checkmk's docs call its settings
   "quite overwhelming").

4. **Tiny, self-hosted, air-gapped-friendly.** One small FastAPI app; deploy native
   (systemd + nginx) or container (Podman/Docker); fully offline / air-gapped installs are
   first-class. Fits government / regulated / Haven / gemeente buyers where data must stay
   in-house.

5. **Works on free Checkmk Raw edition.** No license tier required — pure presentation layer.
   Checkmk's own multi-tenant/MSP features are commercial-edition-gated; the Grafana datasource
   historically needed Enterprise (only recently works on Raw).

6. **Brandable client-portal feel.** Optional company logo, optional HTTP basic auth, optional
   support-contact footer, custom title, per-site filtering (distributed monitoring aware).

7. **Zero-maintenance display.** Auto-refresh every 30s, dark NOC-wall-friendly theme,
   all Checkmk data HTML-escaped (XSS-safe).

---

## Validated market demand (why anyone cares)

- **STRONGEST — "show customers/stakeholders status without a Checkmk login."** Multi-year
  Checkmk and LogicMonitor feature requests ask for exactly a login-free customer view.
- **STRONG — "expose status without exposing the tool / internal data."** MSPs want a curated
  view, not console access, for clients.
- **STRONG (design) — NOC wallboard / big-screen "only show problems."**
- **MEDIUM — acknowledged-with-ticket vs unhandled** (established practice to put the ref in
  the ack comment; displaying it is the gap we fill).
- **MEDIUM — MSPs juggling many customer sites** (mostly a cost/licensing story; we're a
  presentation layer even on Raw).
- **MEDIUM — Checkmk UI too complex** for non-technical viewers.
- **WEAK–MEDIUM — air-gapped status page** (lead with this only for gov/regulated audiences).

Marketing lead order: client-safe status view (no console access) as headline → NOC "problems
only" as the demo → ticket extraction as the differentiator → air-gapped for regulated buyers.

---

## Honest limits (state these plainly — credibility is the whole game for self-hosted tools)

- **No per-client data isolation.** Basic auth is all-or-nothing per site: anyone who can open
  the page sees every problem for that site. True multi-tenant scoping needs native Checkmk
  contact-group RBAC or the paid MSP edition. Do **not** imply per-customer data separation.
- **It mirrors Checkmk; it is not observability.** No metrics, logs, traces, historical graphs,
  independent checks, or notifications. Not a Grafana or Uptime Kuma replacement — it shows what
  Checkmk already knows.
- **Not real-time.** Polls every ~30s — say "auto-refreshing (30s)", never "real-time".
- **Depends on Checkmk being reachable** (shows a connection error otherwise) and on the
  ack-comment ticket convention for the ticket signal.

---

## Competitive context (for honest framing)

- **No direct competitor** to "a thin, safe, read-only view layer on Checkmk."
- Real alternatives = ways to expose Checkmk's own data (native views/dashboards + contact-group
  RBAC, NagVis/Orbvis wallboards, Grafana + Checkmk datasource, paid MSP/Ultimate tier) — all
  expose the full UI and/or need deliberate RBAC/anonymous setup.
- General status tools (Uptime Kuma MIT, Gatus Apache-2.0, Statping-ng GPL-3.0, Cachet) run
  their *own* checks and don't read Checkmk or have an ack/ticket concept — wrong layer.
- Where alternatives genuinely win: Grafana (history/graphing/alerting), Uptime Kuma
  (independent checks + notifications + incident history), native RBAC / paid MSP (real
  per-tenant data isolation).

### ⚠️ Must-not-claim (accuracy guardrails)
- **Do NOT claim Checkmk "can't share without a login."** Checkmk 2.5 (2026) shipped native
  login-less "externally sharable dashboards" (Werk #19333). Differentiate instead on: curated
  non-OK-only view, ticket extraction, credentials never in the browser, no share-token that
  silently breaks when the dashboard is edited, works on Raw and older versions, tiny
  air-gapped deploy.
- Don't call it "observability", "real-time", "enterprise-grade", "AI-powered", or
  "single pane of glass" more than once.

---

## Positioning vocabulary
**Use:** self-hosted · air-gapped · on-prem · read-only monitoring view · client-facing /
customer-facing · MSP client portal · status wallboard · NOC dashboard · white-label / branded ·
at-a-glance red/amber/green health · Checkmk REST API.
**Avoid:** full observability platform · real-time · enterprise-grade / next-gen / seamless /
unified platform · AI-powered.
