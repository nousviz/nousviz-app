import { apiFetch } from "@/lib/api";

/**
 * P215: email (SMTP) is optional. Whether it is set up decides the default
 * channel for a new alert, so an install without SMTP never creates alerts
 * that can't be delivered. `null` when the status can't be read.
 */
export async function fetchSmtpConfigured(): Promise<boolean | null> {
  try {
    const r = await apiFetch("/api/health/config");
    if (!r.ok) return null;
    const d = await r.json();
    return Boolean(d?.smtp_configured);
  } catch {
    return null;
  }
}

/** Email when it is set up, otherwise the log. */
export function defaultAlertChannels(smtpConfigured: boolean | null): string[] {
  return smtpConfigured ? ["email"] : ["log"];
}
