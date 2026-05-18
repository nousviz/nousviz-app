/**
 * Shared health check evaluation.
 *
 * Derives a list of pass/warn/fail checks from the health and config API responses.
 * Used by Topbar, DashboardPage, and anywhere else that shows system status.
 */

export interface HealthCheck {
  id: string;
  label: string;
  status: "pass" | "warn" | "fail" | "info";
  detail: string;
  action?: { label: string; href?: string; onClick?: string }; // onClick is a named action, not a function (for serialization)
  /** Grouping bucket for the System Status page (v0.8.4 P115). Topbar
   * dropdown ignores this and renders the flat list. */
  group?: "services" | "security" | "configuration";
  /** Optional structured detail for the expanded per-check panel (P115).
   * Rendered as key/value rows below the main row when the operator
   * expands it. */
  expanded?: { label: string; value: string }[];
}

export interface ServiceStatus {
  status: string;
  version?: string;
  tables?: number;
  error?: string;
}

export interface HealthData {
  status: string;
  version?: string;
  services?: {
    postgres?: ServiceStatus;
    [name: string]: ServiceStatus | undefined;
  };
  stats?: {
    active_alerts?: number;
    fusions?: number;
    annotations?: number;
    installed_plugins?: number;
    active_shares?: number;
  };
  ssl?: { enabled: boolean; type: string; domain?: string; expires?: string };
  timestamp?: string;
}

export interface ConfigData {
  encryption_key_set: boolean;
  auth_required: boolean;
  superadmin_exists: boolean;
  postgres_password_is_default: boolean;
  smtp_configured?: boolean;
  update_available?: boolean;
  update_latest?: string;
  update_current?: string;
}

/**
 * Build the "detail" line shown next to a connected service label in the health dropdown.
 * Same format across all services so operators don't wonder why Postgres shows tables but
 * ClickHouse shows version (and vice-versa):
 *   Connected · <version> · <N> tables   (both)
 *   Connected · <version>                 (version only)
 *   Connected · <N> tables                (tables only)
 *   Connected                             (neither — fallback)
 */
export function formatServiceDetail(version?: string, tables?: number): string {
  const parts: string[] = ["Connected"];
  if (version) parts.push(version);
  if (typeof tables === "number") parts.push(`${tables} ${tables === 1 ? "table" : "tables"}`);
  return parts.join(" · ");
}

// ── SSL expiry parsing + countdown (P115) ───────────────────────────
//
// Backend returns `ssl.expires` as `"Jul 15 08:01:02 2026 GMT"` — the
// openssl default format. Date() parses this directly.
//
// Severity thresholds chosen to give operators enough runway:
//   > 30 days  → pass
//   7-30 days  → warn ("schedule renewal")
//   0-7 days   → fail ("renew urgently")
//   expired    → fail ("expired N days ago")

export interface SslExpiryInfo {
  daysLeft: number | null;  // null if unparseable
  status: "pass" | "warn" | "fail";
  detail: string;           // "expires in 82 days" | "expired 3 days ago" | ...
}

export function parseSslExpiry(expires?: string): SslExpiryInfo {
  if (!expires) return { daysLeft: null, status: "pass", detail: "" };
  const expiry = new Date(expires);
  if (Number.isNaN(expiry.getTime())) {
    return { daysLeft: null, status: "pass", detail: "" };
  }
  const now = Date.now();
  const msLeft = expiry.getTime() - now;
  const daysLeft = Math.floor(msLeft / (1000 * 60 * 60 * 24));

  if (daysLeft > 30) {
    return { daysLeft, status: "pass", detail: `expires in ${daysLeft} days` };
  }
  if (daysLeft > 7) {
    return { daysLeft, status: "warn", detail: `expires in ${daysLeft} days — schedule renewal` };
  }
  if (daysLeft > 0) {
    return {
      daysLeft,
      status: "fail",
      detail: `expires in ${daysLeft} ${daysLeft === 1 ? "day" : "days"} — renew urgently`,
    };
  }
  if (daysLeft === 0) {
    return { daysLeft, status: "fail", detail: "expires today — renew now" };
  }
  const daysAgo = Math.abs(daysLeft);
  return {
    daysLeft,
    status: "fail",
    detail: `expired ${daysAgo} ${daysAgo === 1 ? "day" : "days"} ago`,
  };
}

export function evaluateChecks(
  health: HealthData | null,
  config: ConfigData | null,
): HealthCheck[] {
  // Don't evaluate until data has loaded
  if (!health) return [];

  const isLocal =
    typeof window !== "undefined" &&
    (window.location.hostname === "localhost" ||
      window.location.hostname === "127.0.0.1");

  const checks: HealthCheck[] = [];

  // PostgreSQL and every other registered service share the same detail-string format:
  //   Connected · <version> · <N> tables      (both present)
  //   Connected · <version>                   (version only)
  //   Connected · <N> tables                  (tables only)
  //   Connected                               (neither — shouldn't happen for postgres)
  //   <error>                                 (disconnected)
  const pgStatus = health.services?.postgres?.status;
  const pgVersion = health.services?.postgres?.version;
  const pgShortVersion = pgVersion?.replace(/^PostgreSQL\s+/, "").split(" ")[0];
  const pgTables = health.services?.postgres?.tables;
  checks.push({
    id: "postgres",
    label: "PostgreSQL",
    group: "services",
    status: pgStatus === "connected" ? "pass" : "fail",
    detail:
      pgStatus === "connected"
        ? formatServiceDetail(pgShortVersion, pgTables)
        : "Disconnected",
    expanded:
      pgStatus === "connected"
        ? [
            ...(pgVersion ? [{ label: "Version", value: pgVersion }] : []),
            ...(typeof pgTables === "number" ? [{ label: "Tables", value: String(pgTables) }] : []),
          ]
        : undefined,
  });

  // Utility services (ClickHouse, future utilities) — any service beyond postgres.
  // Service labels — short all-letter names are acronyms (sdk, https), uppercase them.
  // Multi-word names get title-case ("clickhouse" stays "Clickhouse" — close enough).
  const labelForService = (n: string): string => {
    if (n.length <= 4 && /^[a-z]+$/.test(n)) return n.toUpperCase();
    return n.charAt(0).toUpperCase() + n.slice(1);
  };

  // A service is "healthy" if its status is connected OR (for non-network
  // services like the SDK) "available". Both are the green-light states.
  const HEALTHY_STATUSES = new Set(["connected", "available"]);

  // Disconnected utilities are warnings (not fail) — analytics plugins depending on them
  // will surface their own failures, and the platform itself still runs without them.
  if (health.services) {
    for (const [name, svc] of Object.entries(health.services)) {
      if (name === "postgres" || !svc) continue;
      const ok = HEALTHY_STATUSES.has(svc.status);
      const notConfigured = svc.status === "not_configured";
      const label = labelForService(name);
      const offlineDetail = notConfigured
        ? "Not configured"
        : svc.error
        ? svc.error
        : svc.status
        ? svc.status.charAt(0).toUpperCase() + svc.status.slice(1)
        : "Disconnected";
      // Detail line: for "connected" services show the standard
      // "Connected · version · tables" format; for "available" services
      // (SDK) show just "Available · version" since they don't have tables.
      const okDetail = svc.status === "available"
        ? `Available${svc.version ? ` · ${svc.version}` : ""}`
        : formatServiceDetail(svc.version, svc.tables);
      checks.push({
        id: `service_${name}`,
        label,
        group: "services",
        status: ok ? "pass" : notConfigured ? "info" : "warn",
        detail: ok ? okDetail : offlineDetail,
        expanded: ok
          ? [
              ...(svc.version ? [{ label: "Version", value: svc.version }] : []),
              ...(typeof svc.tables === "number"
                ? [{ label: "Tables", value: String(svc.tables) }]
                : []),
            ]
          : undefined,
      });
    }
  }

  // HTTPS — only on non-localhost.
  // SSL expiry countdown (P115 v0.8.4): parse the `expires` field and
  // escalate severity as the date approaches.
  if (!isLocal) {
    if (!health?.ssl) {
      checks.push({
        id: "ssl",
        label: "HTTPS",
        group: "security",
        status: "warn",
        detail: "Not configured",
        action: { label: "Configure", onClick: "ssl-setup" },
      });
    } else {
      const expiry = parseSslExpiry(health.ssl.expires);
      const typeLabel =
        health.ssl.type === "letsencrypt" ? "Let's Encrypt" : "Self-signed";
      // When we can't parse the expiry, fall back to the simple "configured"
      // signal rather than spuriously raising severity.
      const unparsed = expiry.daysLeft === null;
      // B137 follow-up: don't repeat the domain in the inline detail —
      // the operator is already on that domain. Domain stays in the
      // expanded panel for cases where someone is debugging from
      // elsewhere (curl, screenshot, multi-host setup).
      const detailParts: string[] = [typeLabel];
      if (!unparsed) detailParts.push(expiry.detail);
      checks.push({
        id: "ssl",
        label: "HTTPS",
        group: "security",
        status: unparsed ? "pass" : expiry.status,
        detail: detailParts.join(" · "),
        expanded: [
          { label: "Type", value: typeLabel },
          ...(health.ssl.domain ? [{ label: "Domain", value: health.ssl.domain }] : []),
          ...(health.ssl.expires
            ? [{ label: "Expires", value: health.ssl.expires }]
            : []),
          ...(expiry.daysLeft !== null
            ? [
                {
                  label: "Days left",
                  value: String(expiry.daysLeft),
                },
              ]
            : []),
        ],
        // Only surface the Configure action when SSL isn't set up; once
        // set up, renewal is handled out-of-band (certbot, cloudflare, etc).
      });
    }
  }

  // Authentication — only on non-localhost.
  if (!isLocal) {
    const authOk = config?.auth_required && config?.superadmin_exists;
    checks.push({
      id: "auth",
      label: "Authentication",
      group: "security",
      status: authOk ? "pass" : "warn",
      detail: authOk
        ? "Multi-user accounts enabled"
        : !config?.auth_required
          ? "Disabled"
          : "No superadmin user yet — complete the setup wizard",
      action: authOk
        ? undefined
        : { label: "Settings", href: "/settings/security" },
    });
  }

  // Encryption key
  if (config) {
    checks.push({
      id: "encryption",
      label: "Encryption key",
      group: "security",
      status: config.encryption_key_set ? "pass" : "warn",
      detail: config.encryption_key_set
        ? "AES-256-GCM · key set"
        : "Not set — credentials stored unencrypted",
      action: config.encryption_key_set
        ? undefined
        : { label: "Fix now", onClick: "setup-wizard" },
    });
  }

  // Default Postgres password — non-localhost only.
  // P115: v0.8.1 (S108) removed the nousviz_dev default entirely, so this
  // check is no longer strictly reachable. Keep the branch — if an
  // upgraded install somehow still reports the flag, we surface it.
  if (!isLocal && config?.postgres_password_is_default) {
    checks.push({
      id: "db_password",
      label: "Database password",
      group: "security",
      status: "warn",
      detail: "Using publicly known default password",
      action: { label: "Fix now", onClick: "setup-wizard" },
    });
  }

  // SMTP
  if (config) {
    checks.push({
      id: "smtp",
      label: "Email (SMTP)",
      group: "configuration",
      status: config.smtp_configured ? "pass" : "warn",
      detail: config.smtp_configured ? "Configured" : "Not configured",
      action: config.smtp_configured
        ? undefined
        : { label: "Configure", href: "/settings/email" },
    });
  }

  // Active shares — info indicator (not a warning — shares are intentional)
  const activeShares = health.stats?.active_shares ?? 0;
  if (activeShares > 0) {
    checks.push({
      id: "shares",
      label: "Shared links",
      group: "configuration",
      status: "pass",
      detail: `${activeShares} Active`,
      action: { label: "Manage", href: "/shares" },
    });
  }

  // Update available
  if (config?.update_available && config.update_latest) {
    checks.push({
      id: "update",
      label: "Update available",
      group: "configuration",
      status: "info",
      detail: `${config.update_latest} (current: ${config.update_current || "unknown"})`,
      action: { label: "Details", href: "/admin/cli" },
    });
  }

  return checks;
}

export function summarize(checks: HealthCheck[]): {
  level: "healthy" | "warning" | "critical" | "loading";
  label: string;
} {
  if (checks.length === 0) return { level: "loading", label: "Checking…" };

  const fails = checks.filter((c) => c.status === "fail").length;
  const warns = checks.filter((c) => c.status === "warn").length;

  if (fails > 0) return { level: "critical", label: "Critical" };
  if (warns > 0) return { level: "warning", label: `${warns} Warning${warns !== 1 ? "s" : ""}` };
  return { level: "healthy", label: "Healthy" };
}

/**
 * Canonical label for a level — title-case, consistent across the app.
 * Use this everywhere a raw `level` would otherwise be rendered so the
 * topbar and the overview page never disagree on casing.
 */
export function labelForLevel(level: string): string {
  switch (level) {
    case "healthy": return "Healthy";
    case "warning": return "Warning";
    case "critical": return "Critical";
    case "loading": return "Checking…";
    default: return level.charAt(0).toUpperCase() + level.slice(1);
  }
}

/**
 * Count pass/warn/fail checks in a list. Used for the inline summary on
 * each history row.
 */
export function countByStatus(checks: { status: string }[]): { pass: number; warn: number; fail: number } {
  const counts = { pass: 0, warn: 0, fail: 0 };
  for (const c of checks) {
    if (c.status === "pass" || c.status === "info") counts.pass++;
    else if (c.status === "warn") counts.warn++;
    else counts.fail++;
  }
  return counts;
}
