# Checkmk Dashboard — Gaps We Fill & Positioning Research

Research date: 2026-10-26. All claims below are from web sources (cited inline), not memory.

---

## 1. Checkmk gaps a lightweight read-only dashboard fills

### 1.1 Native dashboards are permission-scoped and break for simple viewers
Checkmk's built-in dashboards count hosts/services via Livestatus and are filtered by each
user's contact permissions. A user who is only a *service* contact (not a host contact) sees
**0 hosts** on the host-state widgets — the dashboard silently empties out instead of showing a
simple status. The fix for this was requested and marked **"Not planned."**
- Forum: host status invisible to service-only contacts — <https://forum.checkmk.com/t/show-host-status-for-users-who-are-only-service-contacts/33060>
- Feature request, declined — <https://features.checkmk.com/suggestions/323555/allow-users-who-are-not-hosts-contacts-to-see-the-state-of-the-host>

The "main" dashboard in commercial editions is further restricted to admins/guests, and its
problem graphs explicitly *do not* respect per-user permissions (so you can't safely expose it
to a client).
- Werk #5486 — <https://checkmk.com/de/werk/5486>

**Gap we fill:** credentials stay server-side (one automation user), so the viewer sees a
consistent, complete at-a-glance status regardless of per-user contact scoping — without being
granted a Checkmk login at all.

### 1.2 No native "simple, client-facing, at-a-glance" view
There is no documented way to make a Checkmk dashboard read-only for a non-technical role.
Community workarounds are hacky (e.g. building widgets off the site's own "Site statistics"
service) or involve standing up a NOC wallboard the client still logs into. The practitioner
pain of "clean green/yellow/red for a support team / TV wall" is a recurring ask across the
monitoring space.
- INOC on NOC dashboards — <https://inoc.com/blog/noc-dashboards>
- Clean health dashboard pattern (green/yellow/red) — <https://acewinds.atlassian.net/wiki/x/IoBDAQ>

**Gap we fill:** purpose-built 3-bucket view (Critical / Warning / Acknowledged), Checkmk UI
stays hidden, nothing to misconfigure, nothing to click into.

### 1.3 Acknowledgement + ticket linkage is a real, unsolved-natively pattern
This is the strongest validation of the product's core idea. Checkmk's acknowledgement comment
field renders a URL as a clickable link, but there is **no native field** for a ticket number
and **no native "store the ticket ID with the problem"** capability.
- Acknowledgement docs (comment field: "You can include a URL ... which will be replaced by a
  clickable link"; persistent comments survive ack removal) —
  <https://docs.checkmk.com/latest/en/basics_ackn.html>

The community explicitly proposes exactly our pattern — put the ticket ID in a (persistent)
acknowledgement comment and read it back — because the native ServiceNow plugin's full-text
search for the problem ID is expensive. This is an open feature request, i.e. a real gap:
- Checkmk Ideas "Store a ticket number ... with the checkmk problem" —
  <https://ideas.checkmk.com/suggestions/670664/comment/754718>
- Jira integration is commercial-only; only in 2.4.0b2+ does the notification result even
  include the issue number (Werk #17705) — <https://checkmk.com/werk/17705>
- Jira notifications doc — <https://docs.checkmk.com/latest/en/notifications_jira.html>

**Gap we fill:** we parse the ticket reference (plain `INC-1234` or full Jira/helpdesk URL,
configurable case-insensitive prefix) out of the ack comment and surface it — turning the one
native affordance (a comment that can hold a URL) into a first-class, visible ticket link. No
commercial edition, no ITSM plugin required.

### 1.4 REST API approach is sound (verified)
Our approach — `GET /domain-types/service/collections/all` with a `query` filter on `state`
and requested `columns` — matches the documented/working community pattern.
- Working forum example filters `state != 0`, returns `state`, `acknowledged`, `host_name`,
  `description` — <https://forum.checkmk.com/t/retreive-a-list-of-hosts-by-theyr-status-using-rest-apis/52328>
- Columns / problem-defining columns thread —
  <https://forum.checkmk.com/t/rest-api-show-all-monitored-services-columns-defining-problem/38538>
- REST-API code examples (KB) —
  <https://checkmk.atlassian.net/wiki/spaces/KB/pages/9473812/REST-API+code+examples>

Confirmed gotchas (already captured in the project's CLAUDE.md, and corroborated here):
- Endpoint is a thin Livestatus window; it does **not** appear in Swagger/ReDoc, so column
  errors ("Unknown column") are common — verify columns against your version's ReDoc.
- Comments-with-info is the way to read ack comment text; a plain `comments` column returns IDs.
  Note a reliability caveat: one user reported the collection endpoint intermittently drops
  comment info / some hosts — <https://forum.checkmk.com/t/rest-api-api-1-0-domain-types-service-collections-all-looses-comments-info-temporarily/46203>
- Ack *expiry* is commercial-only; the open-source ack is "until next state change" or sticky
  (matters for how long our acknowledged bucket stays populated) —
  <https://docs.checkmk.com/latest/en/basics_ackn.html>

**Takeaway:** REST-over-Livestatus is the right, supported choice for a read-only external view.
For very high object counts, Livestatus directly or a saved view exported via `output_format`
is the scale path, but REST is correct for this product.

---

## 2. Positioning vocabulary / SEO keywords

### 2.1 Credible terms to use (searched for, used by real product pages)
| Term | Why it's credible / where it's used |
|---|---|
| **single pane of glass** (SPOG) | Widely used category term; established definition = one display consolidating many sources. Overused but still the #1 search term — use once, back it with specifics. <https://last9.io/blog/what-is-single-pane-of-glass-monitoring-and-how-it-works.md> |
| **NOC dashboard / NOC wallboard / monitor wall** | Real operational vocabulary; vendors (Fortinet FortiView, SolarWinds NOC View) position for "a monitor wall in your NOC." <https://inoc.com/blog/noc-dashboards> , <https://docs.fortinet.com/document/forticentral/7.2.0/user-guide/724874> |
| **read-only monitoring view / read-only dashboard** | Concrete, differentiating, honest for this product. New Relic shipped "read-only dashboards" as a named feature. <https://docs.newrelic.com/whats-new/2026/01/whats-new-01-19-read-only-dashboards/> |
| **status wallboard / status page** | "status page" is a huge category (Statuspage, Uptime Kuma, Cachet, Gatus). Positions us next to tools people already search. <https://betterstack.com/community/comparisons/statuspage-vs-uptime-kuma.md> |
| **self-hosted** | Strong, credible, high-intent keyword in this niche (Uptime Kuma, Gatus). "control of your data", "single Docker container". <https://openalternative.co/alternatives/statuspage> |
| **on-prem / on-premises** | Credible for the enterprise/gov buyer; pairs with self-hosted. |
| **air-gapped** | Highly credible *and* differentiating for gov/compliance (Haven/Common Ground). Few status tools claim it; we genuinely deploy air-gapped. Use it. |
| **client-facing / customer-facing** | Real MSP vocabulary. The value prop "make invisible work visible to the client" is the standard MSP framing. <https://blog.cloudradial.com/7-things-to-know-about-white-label-msp-client-portals> |
| **MSP client portal / customer portal** | The dominant label for this exact use case. <https://blog.cloudradial.com/7-things-to-know-about-white-label-msp-client-portals> |
| **white-label / branded (logo)** | Concrete; maps to our optional-logo feature. Means "client sees your branding / your domain." <https://www.manageengine.com/za/cloudspend/help/customer-portal.html> |
| **at-a-glance / green-yellow-red health** | Honest, describes the actual UX; resonates with the TV-wall buyer. <https://acewinds.atlassian.net/wiki/x/IoBDAQ> |
| **Checkmk REST API / Checkmk dashboard** | Primary long-tail SEO: people searching for exactly this integration. |

### 2.2 Overused fluff / clichés to avoid (or use sparingly, once, with proof)
- **"single pane of glass"** — still worth one mention for SEO, but it's the most worn-out phrase
  in monitoring; don't lead the whole pitch with it. Back it with the concrete 3-bucket view.
- **"full observability" / "observability platform"** — we are *not* observability (no metrics/
  logs/traces). Claiming it is dishonest and invites unfavourable comparison to Grafana/Datadog.
- **"real-time"** — we poll every 30s. "auto-refreshing (30s)" is honest and still appealing;
  "real-time" overpromises.
- **"enterprise-grade" / "next-gen" / "powerful" / "seamless" / "unified platform"** — generic
  SaaS filler, zero information, erodes credibility with the technical buyer.
- **"AI-powered"** — irrelevant and a red flag here.

Rule of thumb: lead with what it *is* (a tiny read-only Checkmk status view with ticket links),
use SPOG/NOC/wallboard as SEO anchors, and reserve "air-gapped / self-hosted / client-facing"
as the genuine differentiators.

---

## 3. What makes a great self-hosted-tool README (structure + sources)

### 3.1 The converging structure (skimmer must "get it" in ~10s)
1. **Centered logo + one-line value statement** (hero line: what it is, for whom).
2. **Badges row** (Shields.io): license, release/version, build, maybe Docker pulls / stars.
   Keep it to a few meaningful ones — not a wall.
3. **Hero screenshot / GIF, early** — above the feature list. For a dashboard this is the single
   most important element: show the actual green/yellow/red view with a ticket link visible.
4. **Short feature bullets** (scannable, not a paragraph).
5. **Quick start / install** — copy-pasteable. For us: the FastAPI + `.env` path, and the
   Podman/Docker path, plus a one-liner that it runs air-gapped.
6. **Configuration table** (our `.env` vars — already well-structured in CLAUDE.md).
7. **Credibility signals** last: license, screenshot of real use, link to deeper docs.

Uptime Kuma is the canonical reference layout for this niche: centered logo → one-liner →
sponsor/translation badges → wide dashboard screenshot → live demo → features → Docker Compose
quick start.
- Uptime Kuma README (mirror) — <https://github.com/xxpandora/uptime-kuma/blob/master/README.md>

### 3.2 Best-practice sources
- Standard-Readme spec (closest to a formal standard) —
  <https://awesome.ecosyste.ms/projects/github.com%2Frichardlitt%2Fstandard-readme>
- Art of README — <https://best-of-web.builder.io/library/hackergrrl/art-of-readme>
- "How to Write a Killer README" (FOSDEM 2025) — README's main job is getting people started.
- README best-practices roundup (title + value statement, feature summary, install, usage,
  credibility signals; beware doc drift) — <https://www.docuwriter.ai/posts/readme-best-practices>

### 3.3 Concrete do's for *this* project
- Hero line candidate: "A tiny, read-only Checkmk status dashboard — Critical / Warning /
  Acknowledged, with ticket links. Self-hosted, air-gapped-friendly, read-only by design."
- Put the screenshot (with a parsed `INC-1234` / Jira link visible) directly under the badges.
- Keep it short; the `.env` table carries the detail. Don't pad with observability buzzwords.
- Badges that are honest here: license, latest release, "self-hosted", Python/FastAPI, Docker.
