# NousViz Roadmap

> Current: **v1.0.0** — first public release.

## Released

### v1.0.0 — initial public release
- [x] **Data Explorer** — Connection → Table → Row drilldown across every installed plugin and every Postgres connection. Sort, filter, save view as widget.
- [x] **Dashboard builder** — Free-form grid with drag-to-resize, inline heading and text edits, plugin-rendered and operator-built widgets composed side by side.
- [x] **Plugin ecosystem** — YAML manifests, marketplace install, three-tier source resolution (official / community / private), commit-SHA verification, SSRF-protected install path, pip-isolated plugin envs, per-plugin Postgres role.
- [x] **Plugin SDK** — `pip install nousviz-sdk` for plugin authors, stable contract surface, starter template, OpenAPI-generated Python + TypeScript clients.
- [x] **Alerts** — Threshold (drop / rise / absolute) and zero-check alerts on any numeric metric, with email and webhook delivery.
- [x] **Webhooks** — Inbound URLs for ingest; outbound POST for Slack / Discord / PagerDuty / arbitrary endpoints.
- [x] **Multi-user + RBAC** — Per-user email + password auth, 4-role RBAC (viewer / analyst / admin / superadmin), invite flow, session management, recovery script.
- [x] **Annotations** — Tag events across datasets with notes and scoring.
- [x] **MCP server** — AI agents can query installed plugins via FastMCP.
- [x] **Native install** — `scripts/setup.sh` installs Postgres + Node + nginx on macOS / Debian / RHEL / Arch. No Docker required. `--server` mode finishes nginx + pm2 end-to-end.
- [x] **OAuth** — Core-owned OAuth callback for plugins that need third-party auth.
- [x] **Encrypted credentials** — AES-256-GCM at rest, per-user encryption key.

## Next — v1.1

The v1.0 surface is intentionally narrow. v1.1 priorities are operator-quality-of-life and the surfaces that didn't make the v1.0 cut.

- [ ] **Hot-reload plugins** — Install / upgrade plugins without restarting the API process.
- [ ] **Plugin update flow** — Diff preview, non-destructive upgrade with migration tracking.
- [ ] **Mobile-responsive UI** — The desktop builder is the v1.0 target; v1.1 makes dashboards readable on phones.
- [ ] **Verified-publisher badge** — Trust signal in the marketplace for community plugins.
- [ ] **Plugin health dashboard** — Last-sync time, error rate, sync-job latency per plugin.

## Beyond v1.1

These are real but unscheduled. They unlock specific user types, not core functionality.

- **SSO (OIDC / SAML)** — For teams that need to remove per-user passwords.
- **Audit-log export** — Tamper-evident export for compliance use cases.
- **Plugin marketplace ratings + reviews** — Community trust signal.
- **Plugin developer analytics** — Build time, install count, error-rate dashboard for publishers.
- **Revenue sharing for paid plugins** — Stripe integration for plugin publishers.

---

## Long-Term Vision

**NousViz = data intelligence platform + plugin ecosystem**

Two layers:

1. **Platform** — open-source, self-hosted data engine (Postgres + optional ClickHouse, Python + React).
2. **Plugins** — data connectors, dashboards, alerts, AI features — all installable from the marketplace.

WordPress, but for data-powered applications.
