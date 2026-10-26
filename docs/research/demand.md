# Demand research — read-only Checkmk status dashboard

Research date: 2026-10-26. Method: web search + page fetches across the Checkmk Ideas portal,
Checkmk/Zabbix/LogicMonitor community forums, MSP forums (Technibble, dmarcian), vendor docs and
design blogs. Reddit/HN threads surfaced only as secondhand summaries (search is US-only and many
primary community pages 403 on fetch), so direct Reddit voices are thinner than hoped — flagged
below where it matters.

Product recap (what we're validating demand for): a lightweight, read-only web view in front of an
existing Checkmk REST API. Shows only non-OK services in three buckets — Critical / Warning /
Acknowledged — where "Acknowledged" means acked in Checkmk with a comment containing a ticket ref
(INC-1234 / Jira URL), which it extracts and shows. Credentials stay server-side, no write path,
Checkmk's own UI stays hidden. Tiny deploy, works air-gapped.

---

## Ranked validated demands

### 1. Show customers/stakeholders a status view WITHOUT a Checkmk login — STRONG
This is the single best-evidenced demand, and notably Checkmk itself just shipped a feature for it,
which both validates the need and is a competitive flag (see Risks).

- Checkmk Ideas portal, "Externally sharable dashboards" — a multi-year request with autologin and
  fullscreen-TV requests merged into it. Requester wanted exactly this product's shape:
  > "With multiple dashboards you could use this as customer dashboard... The page should be
  > available without login, but you can modify/create incidents after you are successful logged in."
  Shipped in Checkmk 2.5 (Werk #19333). https://ideas.checkmk.com/suggestions/458651 ; werk:
  https://checkmk.com/werk/19333
- Checkmk forum, sharing dashboards per-affiliate without exposing other affiliates' data — new user
  Josh: "we can't seem to share those dashboards with just this affiliate user without things
  breaking" (one affiliate ~100 dashboards). Native sharing is fiddly and permission-coupled.
  https://forum.checkmk.com/t/how-to-share-dashboards-across-multiple-contact-groups/49076
- LogicMonitor community (MSP): "Is there a way to give a customer view permissions on only a small
  part of the data in our 'central' environment?... Idealy a standarized dashboard showing them only
  what they are allowed to see."
  https://community.logicmonitor.com/discussions/product-discussions/allow-customer-to-view-some-data-outside-their-group/9413
- Zabbix forum: a user asks whether a monitoring overview can be shown to management "without having
  to log in" — thread left unanswered, i.e. no native answer.
  https://www.zabbix.com/forum/zabbix-help/19730-status-of-zabbix-for-normal-user
- Site24x7 MSP best-practices documents the pattern as a product tier: "white-labeled portals
  provide read-only access, and customers only see monitors the MSP has configured."
  https://site24x7.com/help/msp/best-practices/msp-customer.html

### 2. Safely exposing status without exposing the monitoring tool / internal data — STRONG
The "client-safe, read-only, UI hidden" angle has a clear voiced fear behind it.

- Technibble MSP forum: an MSP hesitated to give clients dashboard access, worried clients would
  question indicators they don't understand — paraphrased fear of "hey, why do I see a red X here?"
  Supports the value of a *curated* view (only Critical/Warning/Acknowledged), not raw tool access.
  https://www.technibble.com/forums/threads/gfi-max-client-dashboard-access-w-take-control-viable-to-replace-logmein.54536/
- dmarcian forum (MSP): "client portal access cannot be granted directly to client as per the MSP
  agreement" — fell back to emailed scheduled reports. Contractual/security reasons to not hand over
  the real console. https://forum.dmarcian.com/t/exposing-reporting-to-clients-for-msps/2149
- Checkmk's own public-dashboard caveat reinforces the "client-safe" selling point: shared dashboards
  run with the *sharer's* permissions and query live data on every load, with a token that silently
  breaks on edits — i.e. the native feature has sharp edges a purpose-built read-only proxy avoids.
  https://checkmk.com/werk/19333 , https://checkmk.com/werk/19989

### 3. NOC wallboard / big-screen / "only show problems" at-a-glance view — STRONG (design consensus) / MEDIUM (Checkmk-specific)
The general need is well-established; Checkmk-specific friction is real and documented.

- Checkmk Ideas: "Dashboard - Multiple Dashboard Cycling / Slideshow" for a big screen is still open;
  staff workaround was third-party Dashkiosk or cycling NagVis iframes — i.e. no clean native NOC
  rotation. https://ideas.checkmk.com/suggestions/341931/dashboard-multiple-dashboard-cycling-slideshow
- Checkmk Ideas: "headless-mode (autologin), fullscreen without navigation" was a distinct request
  (merged into #458651). https://features.checkmk.com/suggestions/297387/
- "Only show failures" design principle: Azure NOC write-up — "Only show failures. If dashboard is
  empty, everything's fine." Directly matches this product's non-OK-only model.
  https://dev.to/azurenoob/building-azure-dashboards-for-cloud-noc-teams-what-actually-gets-used-vs-what-gets-ignored-3o75
- Dataplicity wallboard guide: pick "the smallest set of signals," "a chart is not an alert."
  https://docs.dataplicity.com/workflows/design-the-wallboard-for-who-walks-past-it
- VMware NOC guidance: dashboards "must not require an explanation"; a screen that's red all the time
  gets ignored. (via search of docs.vmware.com NOC dashboard guidance)

### 4. Checkmk native UI is complex / overwhelming for an at-a-glance view — MEDIUM
Evidenced, but mostly via reviews and Checkmk's own docs rather than angry community threads.

- Checkmk's own docs admit it: "This selection can sometimes be quite overwhelming, so that one can
  lose sight of the essentials and orientation becomes difficult." https://docs.checkmk.com/latest/en/intro_gui.html
- AWS Marketplace review: "the UI is very complex for a new user"; WATO rulesets "not very
  descriptive." https://aws.amazon.com/marketplace/reviews/reviews-list/prodview-gddkal2hfn7yo
- Caveat: no strong Reddit/HN rant surfaced; treat as a supporting point, not a headline pain.

### 5. MSPs juggling monitoring across many customer sites — MEDIUM–STRONG
Real pain, but it's primarily a multi-tenancy/licensing story; our product only addresses the
*presentation* slice of it.

- Zabbix has "no built-in concept of separate client environments" — MSPs run per-client instances
  or one shared instance with host-group ACLs, both hard to scale. (Flamingo comparison)
  https://www.flamingo.run/blog/best-zabbix-alternative
- Checkmk's full MSP/multi-tenancy features are gated to commercial editions (Raw lacks them).
  https://checkmk.com/product/monitoring-for-msp ; https://docs.checkmk.com/2.4.0/en/managed.html
- Zabbix forum request "track all clients status on one dashboard" (couldn't fetch body, 403;
  title alone evidences the ask). https://www.zabbix.com/forum/zabbix-suggestions-and-feedback/406178
- Our angle: a read-only view pointed at a single (even Raw) Checkmk site gives MSPs a client-facing
  surface without buying the multi-tenant tier — a cost argument.

### 6. Correlating alerts with ticket numbers / distinguishing "being worked on" vs "unhandled" — MEDIUM
The acknowledged-with-ticket concept is validated and maps to a known Checkmk gap, but demand for
*displaying* the ticket ref specifically is inferred more than directly voiced.

- Checkmk converts URLs in ack comments to clickable links and docs recommend putting a ticket ref
  in the ack comment — i.e. the "ticket in the comment" convention is already established practice,
  which our regex extraction builds on. https://www.simplified.guide/checkmk/problem-acknowledge
- Known gap: Checkmk forum — closing/updating tickets is "much more difficult since Check_Mk would
  need to get and keep track of the ticket number." No native ticket-number tracking.
  https://forum.checkmk.com/t/check-mk-english-integration-with-jira-to-open-update-close-tickets/14204
- Jira Service Management integration only syncs ack state one-way; bidirectional is Premium/Enterprise.
  https://support.atlassian.com/jira-service-management-cloud/docs/integrate-with-checkmk/
- MSP alert-fatigue literature broadly wants "acknowledged & being handled" separated from the
  unhandled pile (ScalePad auto-close, Sophos flap-correlation), but none name the exact
  ack-with-ticket-vs-unhandled split — so this is adjacent evidence, not a direct quote.
  https://alertops.com/alert-ticket-noise-reduction/

### 7. Air-gapped / on-prem / data-sovereignty monitoring — WEAK–MEDIUM (demand real, direct evidence thin)
- openstatus (vendor): healthcare/finance/government "require all operational data, status
  dashboards, and system logs to stay entirely within self-managed infrastructure" — marketing
  claim, no regulation cited. https://www.openstatus.dev/blog/self-hosting-openstatus
- SentinelOne (Mar 2026) launched on-prem/air-gapped tier citing "data residency, privacy and
  sovereignty requirements" — but that's endpoint security, not status dashboards.
  https://www.sentinelone.com/press/sentinelone-brings-ai-security-to-on-premise-regulated-sovereign-self-hosted-and-airgapped-environments/
- ONES: air-gapped reporting "a common requirement in highly regulated industries such as finance,
  government, and critical infrastructure." https://ones.com/blog/7-key-pain-points-to-address-when-planning-air-gapped-reporting-and-analytics/
- Caveat: I found no primary source (forum post, procurement doc, Haven/Common Ground reference)
  where someone explicitly demands an *air-gapped monitoring status page*. The tiny/air-gapped deploy
  is a genuine differentiator, but lead with it only for government/regulated (EU, gemeenten) audiences
  where Tim already knows the requirement first-hand — not as broad validated demand.

---

## Strongest for marketing (what to lead with)

1. **"Give customers/clients a status view without a Checkmk login — and without exposing your
   console."** Demands #1 + #2 combined. Best-evidenced, voiced by real MSPs, and the exact fear
   ("why do I see a red X?") argues for a *curated* read-only view. Headline material.
2. **"At-a-glance NOC wall / big screen — only the problems, nothing to explain."** Demand #3. Strong
   design consensus + open Checkmk feature gaps (no clean native rotation/kiosk). Concrete and demo-able.
3. **"Tie each acknowledged alert to its ticket — see what's handled vs. what's still unowned."**
   Demand #6. Differentiator vs. a raw alert list; builds on an existing Checkmk convention and a real
   native gap. Lead with it for ops/NOC teams, support with #7 for regulated buyers.
4. **Supporting, not headline:** Checkmk-UI-too-complex (#4), MSP multi-site cost angle (#5),
   air-gapped/sovereignty (#7, government audiences only).

## Risks / caveats for positioning

- **Checkmk 2.5 shipped native login-less "externally sharable dashboards" (Werk #19333, 2026).**
  This both validates demand #1 and competes with it. Differentiate on: (a) curated non-OK-only view
  vs. a full dashboard, (b) ticket extraction, (c) credentials never in the browser + no token that
  silently breaks on edit (Werk #19989), (d) works on Raw edition / older versions, (e) air-gapped
  tiny deploy. Do NOT market "login-less sharing" as if Checkmk can't do it — it now can.
- Several strongest signals are **vendor docs and feature-request threads, not Reddit/HN rants.**
  US-only search + 403s on primary forum fetches limited direct community voices. The demand is real
  but the "angry user" quotes are thinner than ideal — worth a targeted Reddit pass (r/msp,
  r/sysadmin, r/checkmk) before writing hard social-proof claims.
- Air-gapped/sovereignty (#7) and the exact ack-with-ticket-vs-unhandled split (#6) are the most
  inferred — strong as supporting narrative, weak as standalone evidenced demand.
