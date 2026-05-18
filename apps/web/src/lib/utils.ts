import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

export function formatBytes(bytes: number): string {
  if (bytes >= 1_073_741_824) return `${(bytes / 1_073_741_824).toFixed(1)} GB`;
  if (bytes >= 1_048_576) return `${(bytes / 1_048_576).toFixed(1)} MB`;
  if (bytes >= 1_024) return `${(bytes / 1_024).toFixed(1)} KB`;
  return `${bytes} B`;
}

/**
 * Format a timestamp as a short relative string — "just now", "12s ago",
 * "3 min ago", "2 hours ago", "5 days ago", "3 weeks ago", "4 months ago",
 * "2 years ago". Past timestamps only; future timestamps (shouldn't happen
 * in normal use) render as "in the future".
 *
 * Approximations above days use 30-day months and 365-day years — plenty
 * accurate for a "how long ago" operator signal.
 */
export function formatRelativeTime(iso: string | null | undefined): string {
  if (!iso) return "never";
  const date = new Date(iso);
  if (isNaN(date.getTime())) return "invalid date";

  const diffMs = Date.now() - date.getTime();

  // Future timestamps — used for expiry dates like invite/share expiry.
  // Render as "in X days" / "in X hours" instead of "in the future".
  if (diffMs < -5000) {
    const futureSec = Math.floor(-diffMs / 1000);
    if (futureSec < 60) return "in a few seconds";
    const futureMin = Math.floor(futureSec / 60);
    if (futureMin < 60) return `in ${futureMin} minute${futureMin === 1 ? "" : "s"}`;
    const futureHr = Math.floor(futureMin / 60);
    if (futureHr < 24) return `in ${futureHr} hour${futureHr === 1 ? "" : "s"}`;
    const futureDays = Math.floor(futureHr / 24);
    return `in ${futureDays} day${futureDays === 1 ? "" : "s"}`;
  }

  const absSec = Math.max(0, Math.floor(diffMs / 1000));
  if (absSec < 5) return "just now";
  const sec = absSec;
  if (sec < 60) return `${sec} second${sec === 1 ? "" : "s"} ago`;

  const min = Math.floor(sec / 60);
  if (min < 60) return `${min} minute${min === 1 ? "" : "s"} ago`;

  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr} hour${hr === 1 ? "" : "s"} ago`;

  const days = Math.floor(hr / 24);
  if (days < 7) return `${days} day${days === 1 ? "" : "s"} ago`;

  const weeks = Math.floor(days / 7);
  if (weeks < 5) return `${weeks} week${weeks === 1 ? "" : "s"} ago`;

  const months = Math.floor(days / 30);
  if (months < 12) return `${months} month${months === 1 ? "" : "s"} ago`;

  const years = Math.floor(days / 365);
  return `${years} year${years === 1 ? "" : "s"} ago`;
}

/**
 * Title-case a lowercase status string for display — so "connected" from the
 * API becomes "Connected" in the UI, matching "Healthy" / "Warning" / other
 * title-cased labels.
 *
 * Handles known status words with friendlier phrasing ("never" → "Never run")
 * and falls back to first-letter-upper for unknown values. Returns an empty
 * string unchanged.
 */
export function formatStatus(status: string | null | undefined): string {
  if (!status) return "";
  const s = String(status).trim();
  if (!s) return "";
  const aliases: Record<string, string> = {
    ok:            "OK",
    stale:         "Overdue",
    never:         "Never run",
    "not configured": "Not configured",
    "n/a":         "Not available",
  };
  const lower = s.toLowerCase();
  if (aliases[lower]) return aliases[lower];
  // Title-case: first letter upper, rest as-is so multi-word or already-correct
  // values ("Let's Encrypt", "Apache-2.0") aren't mangled.
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/**
 * Format a timestamp as a friendly absolute string — "Apr 16, 2026 10:58" —
 * using the operator's locale. Pair with formatRelativeTime for a
 * "{relative} · {absolute}" display in tight layouts.
 */
export function formatAbsoluteTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (isNaN(date.getTime())) return iso;
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
