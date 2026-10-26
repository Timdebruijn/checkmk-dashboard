# Competitive landscape — read-only, client/NOC-facing alert view on top of Checkmk

Research date: 2026-10-26. All claims below are sourced inline. Where sources disagreed
(e.g. version numbers), that is flagged rather than smoothed over.

## 0. Framing — most "competitors" are at the wrong layer

The product is a **thin read-only view layer on top of an existing Checkmk**. The honest
market framing is that there is **no direct competitor** doing exactly this. The realistic
alternatives split into three groups, only the first of which actually competes:

1. **Ways to expose Checkmk's own data read-only** — Checkmk native views/dashboards + roles,
   NagVis/Orbvis wallboards, Grafana + Checkmk datasource, Checkmk MSP/Ultimate multi-tenancy.
   *These are the real alternatives.*
2. **Self-hosted status/uptime tools** (Uptime Kuma, Gatus, Statping-ng, Cachet) — these **are**
   the monitoring; they do **not** read Checkmk. Choosing them means not using Checkmk for that
   view. Wrong layer, but a buyer will mention them.
3. **Other monitoring suites' sharing features** (Zabbix, PRTG, Netdata) and **homelab
   launchers** (Dashy/Homepage/Homarr) — comparison context only; not Checkmk-fed triage views.

---

## 1. Comparison table

| Alternative | What it is | License / cost | Self-host & air-gap | Reads Checkmk data | Read-only *client-safe* view | Ack + ticket correlation | Gap it leaves (that our product fills) |
|---|---|---|---|---|---|---|---|
| **Checkmk native views + dashboards + roles/contact groups** | Built-in Multisite GUI | Raw = GPL free; CRE/CEE/CCE tiered | Yes, full on-prem | Yes (native) | Partial — real data-level RBAC via contact groups, but exposes the **full Checkmk UI**; setup is complex; no anonymous page | No dedicated "ack+ticket" triage signal | A locked-down, single-purpose page that never shows the Checkmk UI; zero RBAC wiring to stand up |
| **Checkmk NagVis / Orbvis wallboard** | Map/wallboard add-on | NagVis GPLv2; Orbvis GPL-2.0, v0.1.0 early | Yes | Yes (Livestatus) | Partial — "no sidebar" view exists, but anonymous access needs **credentials in the URL** or a shared login | No | A clean categorized problem list (not a map), safe to expose, no creds in URL |
| **Public/anonymous status page (Checkmk feature)** | — | — | — | — | **Does not exist** — long-standing open feature request; needs GET-login hack (Werk 14261) | No | The missing product: an actual login-free/basic-auth read-only page |
| **Grafana + Checkmk datasource** | BI/graphing front-end | Grafana OSS AGPLv3 free; plugin free | Yes (OSS); plugin signed | Yes (REST API) | Partial — great graphs, but metric/time-series-centric; needs careful anonymous/RBAC setup | No | Problem-triage focus (not graphs); ack+ticket semantics; far smaller footprint |
| **Uptime Kuma** | Self-hosted uptime monitor + status page | MIT | Yes, fully | **No** — monitors endpoints itself | Status page is public/read-only, but of its **own** checks | No | Does not read Checkmk at all; no ack/ticket concept |
| **Gatus** | Config-driven (YAML) health dashboard | Apache-2.0 | Yes | **No** — own checks | Config-only, read dashboard of own checks | No | Same: not a Checkmk view; no ack/ticket |
| **Statping-ng** | Status page w/ web UI (community fork) | GPL-3.0 | Yes | **No** — own checks | Own-check status page | No | Same wrong layer; patchy maintenance |
| **Cachet** | Incident/status-page system (PHP/Laravel) | Open source, self-host | Yes | **No** — manual/incident-driven | Manual status page, not live | No | Not live, not Checkmk-fed, no auto-triage |
| **Checkly** | SaaS synthetic monitoring (Playwright) | Closed SaaS; Starter $0, Team ~$64/mo | **No self-host** | No | SaaS dashboards | No | SaaS-only; irrelevant for air-gapped/on-prem Checkmk |
| **Dashy / Homepage / Homarr** | Homelab start-page dashboards + widgets | Dashy MIT; others OSS | Yes | Only via generic widgets | Launcher tiles, not a problem-triage view | No | Not a categorized Checkmk problem view; not client-safe by design |
| **Zabbix dashboards** | Zabbix's own sharing | GPL (Zabbix) | Yes | No (Zabbix data) | "Public" dashboard is **not truly anonymous** — still hits host/user-group ACLs | No | N/A unless you run Zabbix; still exposes full UI |
| **PRTG maps + read-only user** | Paessler's sharing | Commercial | Yes | No (PRTG data) | Works, but needs a dedicated Read-Only user + group wiring | No | N/A unless you run PRTG; heavier setup |
| **Netdata** | Metrics agent + Cloud | Agent GPL-3.0; Cloud SaaS | Agent yes; sharing leans on Cloud | No (Netdata data) | Agent has **no native auth**; Rooms/sharing rely on Netdata Cloud | No | N/A unless you run Netdata; air-gap sharing weak |
| **Checkmk MSP / Ultimate (multi-tenancy)** | Official MSP edition | Commercial tier | Yes | Yes (native) | Real per-customer data isolation, but it's the **full Checkmk UI** + a licensing tier | No | A simplified client-facing skin without the UI or the licence tier |
| **Site24x7 MSP NOC view** | SaaS MSP NOC tiles | Commercial SaaS | **No** | No (its own data) | Yes (NOC tiles per customer) | No | SaaS-only; not a Checkmk overlay |

---

## 2. Per-competitor notes

### 2.1 Checkmk native (views, dashboards, roles, wallboard)
- No dedicated client-facing read-only wallboard mode ships with Checkmk. A **public,
  login-free status dashboard is an open feature request** on the Checkmk ideas portal, and a
  commenter there literally suggested using Uptime Kuma instead.
  <https://ideas.checkmk.com/suggestions/458651/comment/745623>
- NagVis maps can be opened without the sidebar for a TV; the documented auto-login route
  **embeds username/password in the URL** (or requires a shared read-only account), and GET
  login must be explicitly enabled (Werk 14261). KB tested on 2.4.0p1.
  <https://checkmk.atlassian.net/wiki/spaces/KB/pages/9472218/How-to+access+Nagvis+maps+directly>
- Permissions on published views/dashboards were actually **broken** in early 2.4 (Werk 17852,
  fixed 2.4.0b5 / 2.5.0b1) — evidence that native "publish a safe view" is fiddly.
  <https://checkmk.com/werk/17852>
- **NagVis**: GPLv2 open-source map/visualization add-on (originally Nagios), built into
  Checkmk, Livestatus-fed. <https://docs.checkmk.com/nagvis.html> · <https://sourceforge.net/p/nagvis/>
- **Orbvis**: community successor to NagVis for Checkmk, **early (v0.1.0, GPL-2.0, targets
  2.5)**. <https://exchange.checkmk.com/p/orbvis>
- **Roadmap note (relevant to us):** Werk #19334 (Feb 2026) introduces a **dashboard REST API**
  family (create/edit/clone/show), but it is explicitly placed under the **unstable** API
  version and subject to change. <https://checkmk.com/werk/19334>
- *Where it's genuinely better than us:* Checkmk's **contact-group RBAC is real data-level
  access control**. Our basic-auth gate is coarse — anyone who can open our dashboard sees every
  problem in the configured site. If a client must see only *their* hosts, native roles/contact
  groups (or MSP) do that properly and we do not.

### 2.2 Grafana + Checkmk datasource
- Official signed plugin; as of **v4.0.0 it works with all editions including Raw** (earlier it
  needed Cloud/MSP/Enterprise). Requires Grafana 10.4.18+ and Checkmk 2.3.0+ per the marketplace
  (GitHub README lists older minimums — sources disagree). Upgrading from 3.x requires
  uninstalling the old `tribe-29-checkmk-datasource` plugin first.
  <https://grafana.com/grafana/plugins/checkmk-cloud-datasource/> ·
  <https://grafana.com/grafana/plugins/checkmk-cloud-datasource/changelog/> ·
  <https://docs.checkmk.com/latest/en/grafana.html>
- *Where it's better:* vastly richer historical graphing, templating, alerting, huge ecosystem.
- *Gap:* it is **metric/time-series-centric**, not a problem-triage list; no ack+ticket
  semantics; anonymous/public exposure needs deliberate Grafana config; much heavier stack than
  a single FastAPI file.

### 2.3 Self-hosted status/uptime tools (wrong layer — they ARE the monitor)
- **Uptime Kuma** (MIT), **Gatus** (Apache-2.0), **Statping-ng** (GPL-3.0), **Cachet** (OSS PHP).
  All run their **own** checks and publish a status page of those; **none read Checkmk**, none
  have any acknowledgement/ticket concept tied to Checkmk.
  <https://betterstack.com/community/comparisons/uptime-kuma-alternative/> ·
  <https://www.bitdoze.com/md/uptime-kuma-vs-gatus.md> ·
  <https://alternativeto.net/software/statping-ng> ·
  <https://alternativeto.net/software/cachet/about>
- *Where Uptime Kuma is better:* if the real need is **independent external uptime checks +
  90-ish notification integrations + a polished public status page with incident history**, it
  wins — but that's a different job than "safe window onto Checkmk".
- **Checkly**: SaaS-only synthetic monitoring (Playwright), no self-host; Starter $0 / Team
  ~$64/mo. Irrelevant for on-prem/air-gapped Checkmk shops.
  <https://checklyhq.com/pricing> · <https://betterstack.com/community/comparisons/checkly-alternative/>

### 2.4 Homelab launchers
- **Dashy** (MIT, 50+ widgets incl. uptime/status), Homepage, Homarr are **start-page/launcher**
  dashboards. A widget can surface a status, but they are not a categorized Critical/Warning/
  Acknowledged Checkmk problem triage and are not built to be client-safe.
  <https://railway.com/deploy/dashy> · <https://github.com/m42e/dashy>

### 2.5 Other monitoring suites (context only)
- **Zabbix**: "public" dashboards are **not truly anonymous** — visibility still follows the
  host-group/user-group ACL matrix; a guest can even alter the dashboard. Multiple forum threads
  confirm this is a recurring pain.
  <https://www.zabbix.com/forum/zabbix-help/406721-public-read-only-dashboards-graphs> ·
  <https://www.zabbix.com/forum/zabbix-help/440826-dashboard-data-as-a-guest-user>
- **PRTG**: documented but manual — create a dedicated **Read Only User** account + user group
  to control map/report access. <https://kb.paessler.com/en/topic/763>
- **Netdata**: agent (GPL-3.0) has **no native auth** (community images bolt on nginx basic
  auth); Rooms/sharing/access control effectively depend on **Netdata Cloud**, weak for
  air-gapped. <https://marketplace.microsoft.com/en-ae/product/lynxroute.netdata>

### 2.6 MSP / purpose-built portals
- **Checkmk Ultimate (formerly MSP) multi-tenancy**: official answer for per-customer isolated
  sites with strict data separation via roles/contact groups — but it is a **commercial licence
  tier** and still the **full Checkmk UI**, not a stripped client-facing skin.
  <https://docs.checkmk.com/managed.html> · <https://checkmk.com/product/monitoring-for-msp>
- **Site24x7 MSP NOC view**: scroll-free status tiles per customer — but **SaaS**, its own data,
  not a Checkmk overlay. <https://www.site24x7.com/help/msp/customer-health-view.html>
- **Purpose-built "Checkmk client dashboard"**: search surfaced essentially **only this project**
  (`timdebruijn/checkmk-dashboard`) as a read-only REST-API-fed Critical/Warning/Acknowledged
  page. No other comparable GitHub frontend turned up. <https://github.com/timdebruijn/checkmk-dashboard>

### 2.7 Ticket / acknowledgement correlation (the genuinely distinctive axis)
- The documented path is the **Jira Service Management** integration: acknowledging in Checkmk
  acks the matching JSM alert (bidirectional needs Premium/Enterprise).
  <https://support.atlassian.com/jira-service-management-cloud/docs/integrate-with-checkmk/>
- But Checkmk itself has **no generic mechanism to track/surface a ticket number per alert** —
  the community consensus is you need an incident manager (PagerDuty/OpsGenie) or to patch the
  notification plugin. <https://forum.checkmk.com/t/check-mk-english-integration-with-jira-to-open-update-close-tickets/14204>
  · <https://forum.checkmk.com/t/auto-acknowledge-if-successful-call-to-notification-plugin/35576>
- **No competitor turns "acknowledged + comment contains a ticket number" into a first-class
  at-a-glance triage signal.** That parsing-from-the-ack-comment approach is our novel angle.

---

## 3. Gaps our product uniquely or better fills

1. **A truly client-safe surface.** Only GETs, credentials stay server-side, Checkmk API/OpenAPI
   docs disabled, no user input forwarded. The full Checkmk UI, Grafana, Zabbix, Netdata and
   NagVis-via-URL all need careful RBAC/anonymous-access work (and NagVis auto-login puts creds
   in the URL). We are safe-to-expose **by construction**, not by configuration.
2. **Ack+ticket correlation as a triage signal.** "Acknowledged **and** has a ticket number =
   someone is working on it" — extracted from the ack comment (INC-1234 / Jira URL). Nobody in
   the field does this; the native/Jira paths sync acks but never surface the ticket in a simple
   view.
3. **The missing "public status page for Checkmk."** This is literally an open Checkmk feature
   request; we are the stripped-down answer to it.
4. **Air-gapped / offline-first, tiny footprint.** Single FastAPI app, vendored Bootstrap (no
   CDN), systemd+nginx or Podman/Docker. Fits gemeente/Haven compliance. Grafana's stack,
   Netdata Cloud sharing, and all SaaS options (Checkly, Site24x7) don't.
5. **Purpose-built triage, not a generic canvas.** Three fixed categories answer "what's broken
   and is anyone on it" in one glance — vs Grafana graphs, Dashy tiles, or NagVis maps that a
   client still has to interpret.
6. **No licence tier required.** Works against Checkmk Raw (free). MSP multi-tenancy and
   JSM bidirectional ack sync are paid tiers.

### Be honest — where alternatives genuinely beat us
- **Per-client data isolation:** Checkmk contact-group RBAC and MSP multi-tenancy do real
  data-level filtering. Our basic auth is all-or-nothing per configured site — everyone who can
  open the page sees every problem in that site. This is our weakest axis for true multi-tenant
  MSP use.
- **Historical graphing / trends / alerting:** Grafana is in a different league.
- **Independent external uptime + notifications + incident history:** Uptime Kuma does that
  natively; we show only what Checkmk already knows and send no notifications.
- **Richer visual topology:** NagVis/Orbvis maps convey dependency/topology that a flat list
  does not.

### Sharpest positioning line
"The safe, air-gappable window onto an existing Checkmk — three-category problem triage with
ack+ticket correlation, exposable to a client or NOC without ever showing them the Checkmk UI or
wiring up RBAC." The defensible moat is (1) safe-by-construction read-only exposure and (2) the
ack-comment ticket-extraction signal; the honest weak spot to address next is **per-client data
scoping**, which today only native Checkmk/MSP RBAC delivers.
