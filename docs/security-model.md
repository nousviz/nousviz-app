# Security Model

NousViz's security architecture for self-hosted deployments.

---

## Authentication

NousViz is multi-user only. Each user has their own email, bcrypt-hashed password, role, and session — no shared-password back door.

- Email + bcrypt password authentication
- Session tokens: SHA-256 hashed before storage, raw returned once at login
- Sessions expire after 30 days (configurable via `NOUSVIZ_SESSION_TTL_DAYS`)
- First user on fresh install becomes superadmin via the setup wizard
- Subsequent users join via admin-issued invites (email or manual link)
- Step-up auth for sensitive operations (RBAC matrix edits, impersonation): re-prompts password and grants a 5-minute elevated window
- Password reset via emailed link (requires SMTP configured) or `scripts/reset-password.sh` for the offline case

### API Keys

- Generated via Settings → Security
- SHA-256 hashed before storage; raw key shown once
- No expiry; revocable from the UI
- Scoped to instance-wide access (per-key permissions planned for a later release)

---

## Role-Based Access Control (RBAC)

Four named roles with fixed permission sets:

| Permission | Viewer | Analyst | Admin | Superadmin |
|-----------|:---:|:---:|:---:|:---:|
| Read dashboards, data, alerts | Yes | Yes | Yes | Yes |
| Create/edit alerts, annotations, shares, dashboards | — | Yes | Yes | Yes |
| Upload datasets, trigger plugin sync | — | Yes | Yes | Yes |
| Install/uninstall plugins, manage settings | — | — | Yes | Yes |
| Manage users, invites, roles | — | — | Yes | Yes |
| Promote/demote superadmin | — | — | — | Yes |
| Admin CLI access | — | — | — | Yes |

### Superadmin Invariant

At least one active superadmin must exist at all times. Enforced by both application guards and a PostgreSQL constraint trigger. Cannot be bypassed via the API or direct SQL.

---

## Query API Security

The `/api/query` endpoint accepts SQL for dashboard rendering.

### Defense Layers

1. **Read-only Postgres role**: Unauthenticated queries execute via `SET LOCAL ROLE nousviz_query` — a role with SELECT-only grants on plugin-declared tables. Core tables (users, sessions, API keys) are never accessible.

2. **Regex guards (defense-in-depth)**: Blocked keywords (DELETE, INSERT, UPDATE, DROP, etc.) and blocked table patterns. These are secondary to the role-based enforcement.

3. **Row limits**: Maximum 10,000 rows per query.

4. **Statement timeout**: 30 seconds per query.

5. **Search path**: `SET search_path = public` prevents schema-qualified escape attempts.

### What authenticated users can access

Authenticated queries (with session token or API key) do NOT use the restricted role. They can access core tables for admin tools and dashboards. Write operations are always blocked by regex guards.

---

## Credential Storage

- Plugin API keys and secrets encrypted with AES-256-GCM using `NOUSVIZ_ENCRYPTION_KEY`
- User passwords stored as bcrypt hashes (12 rounds)
- SMTP passwords stored in `.env` (not in the database)
- Session tokens and API keys hashed with SHA-256 before database storage

### Key Rotation

If `NOUSVIZ_ENCRYPTION_KEY` is compromised:

1. Generate a new key
2. Set `NOUSVIZ_ENCRYPTION_KEY_NEW` in `.env`
3. Run the rotation script (re-encrypts all credentials)
4. Replace the old key with the new one
5. Restart the API

---

## Plugin Security (v0.9.0)

### Privilege separation at the database layer (P203)

- Plugin subprocesses connect to Postgres as the `nousviz_plugin` role, not as `nousviz`
- The role has CRUD on the plugin's own declared tables, SELECT on a few core reference tables, and **no access** to: `credentials`, `credential_audit_log`, `users`, `user_accounts`, `user_sessions`, `api_keys`, `deploy_keys`, `plugin_audit_log`, or other plugins' tables
- A malicious plugin running `SELECT * FROM credentials` gets `permission denied for table credentials` from Postgres — this is the OS-level firewall, not plugin-author convention
- Role password is generated per-install by `scripts/setup.sh` (stored in `.env` as `NOUSVIZ_PLUGIN_PASSWORD`)
- Grants are scoped per-plugin at install time based on `databases.postgres.tables` in `plugin.yaml`; revoked at uninstall

### Credential delivery via broker (P208)

- Decrypted plugin credentials never enter subprocess `os.environ` and never appear in `/proc/<pid>/environ`
- The jobs-worker runs a Unix domain socket credential broker (`<repo>/run/creds.sock`, mode 0700) that decrypts credentials in the worker process and delivers them to plugin subprocesses over the socket
- Each subprocess gets a single-use authentication token (32 bytes, 30s TTL) scoped to one plugin id
- A compromised plugin that exfiltrates its token gains nothing: it's already consumed by the time the subprocess has fetched its credentials
- `NOUSVIZ_ENCRYPTION_KEY` exists only in the API and worker processes; never in a plugin subprocess

### Plugin install / sync surface

- Plugin install requires admin role + rate limiting (5 per 5 minutes per IP)
- Install hooks execute bash scripts as the application user — only install plugins from trusted sources
- Plugin sync scripts run as subprocesses with sanitised environment (no `NOUSVIZ_*` env vars except P208's broker identity/context)
- Plugin routes are hot-loaded into the FastAPI process — they share the same Python runtime but connect to Postgres through the scoped role
- 500s from plugin routes land in `app_logs` (source=`plugin_route`) with class + message + traceback tail, so operators see failures without SSH

### Inbound Webhooks

- Webhook ingestion endpoints are public (no auth required)
- Validated by unique slug (URL-safe token)
- Optional HMAC-SHA256 signature verification per endpoint

---

## Network Security

- HTTPS via Let's Encrypt (configured with `scripts/ssl-setup.sh`)
- Nginx reverse proxy with security headers (X-Frame-Options, X-Content-Type-Options, Referrer-Policy)
- API responses include no-cache headers to prevent stale data
- CORS restricted to configured origins
