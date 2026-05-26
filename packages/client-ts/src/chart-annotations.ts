/**
 * Helpers for matching NousViz annotations against a chart's x-axis values.
 *
 * Use these in a custom plugin widget that receives `annotations` from the
 * host DashboardRenderer:
 *
 *   import { annotationsForXValue, type AnnotationLike } from "@nousviz/client";
 *
 *   function MyChart({ annotations = [], data }) {
 *     const matches = (rawX) => annotationsForXValue(annotations, rawX);
 *     // render whatever marker you like at each row whose x matches.
 *   }
 *
 * The host pre-filters annotations by plugin_id, so the array you receive
 * already excludes other plugins' notes. You typically don't need to
 * filter further unless you also want to scope by `dataset`.
 */

// Minimal shape required by the matcher. Re-stated here so plugin authors
// don't need to import the full `AnnotationRow` type — they can hand in
// any object that quacks like an annotation, including the host-supplied
// AnnotationRow (which is intentionally `Record<string, any>`).
export interface AnnotationLike {
  date_start: string;       // ISO date "YYYY-MM-DD"
  date_end?: string | null; // optional inclusive end; null/undefined = point annotation
  severity?: string | null;
  color?: string | null;
}

/**
 * Convert a chart's raw x-axis value into the date range it represents.
 * Supported formats:
 *   - "YYYY-MM-DD"  → that single day
 *   - "YYYY-Www"    → Monday..Sunday of that ISO 8601 week
 *   - "YYYY-MM"     → first..last day of that month
 *
 * Anything else returns null — caller treats it as a categorical x value
 * (e.g. project name on a bar chart) with no date matching possible.
 */
export function xValueToDateRange(raw: unknown): { start: Date; end: Date } | null {
  if (typeof raw !== "string") return null;

  let m = raw.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (m) {
    const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
    return { start: d, end: d };
  }

  m = raw.match(/^(\d{4})-W(\d{2})$/);
  if (m) {
    const monday = isoWeekToMonday(+m[1], +m[2]);
    const sunday = new Date(monday);
    sunday.setUTCDate(monday.getUTCDate() + 6);
    return { start: monday, end: sunday };
  }

  m = raw.match(/^(\d{4})-(\d{2})$/);
  if (m) {
    const first = new Date(Date.UTC(+m[1], +m[2] - 1, 1));
    const last = new Date(Date.UTC(+m[1], +m[2], 0));
    return { start: first, end: last };
  }

  return null;
}

// ISO 8601: week 1 contains the year's first Thursday.
function isoWeekToMonday(year: number, week: number): Date {
  const jan4 = new Date(Date.UTC(year, 0, 4));
  const jan4Day = jan4.getUTCDay() || 7;
  const week1Monday = new Date(jan4);
  week1Monday.setUTCDate(jan4.getUTCDate() - jan4Day + 1);
  const result = new Date(week1Monday);
  result.setUTCDate(week1Monday.getUTCDate() + (week - 1) * 7);
  return result;
}

function annotationDateRange(a: AnnotationLike): { start: Date; end: Date } {
  const start = new Date(`${a.date_start}T00:00:00Z`);
  const end = a.date_end ? new Date(`${a.date_end}T00:00:00Z`) : start;
  return { start, end };
}

function rangesOverlap(a: { start: Date; end: Date }, b: { start: Date; end: Date }): boolean {
  return a.start.getTime() <= b.end.getTime() && b.start.getTime() <= a.end.getTime();
}

/**
 * Return the subset of `annotations` whose date range overlaps the bucket
 * that `rawX` represents. Empty array if rawX isn't a recognised date format.
 */
export function annotationsForXValue<T extends AnnotationLike>(annotations: T[], rawX: unknown): T[] {
  const bucket = xValueToDateRange(rawX);
  if (!bucket) return [];
  return annotations.filter((a) => rangesOverlap(bucket, annotationDateRange(a)));
}

/**
 * Suggested stroke color for an annotation marker, driven by severity.
 * Plugin authors are free to roll their own — this is just a sensible default.
 */
export function annotationStrokeColor(a: AnnotationLike): string {
  if (a.color) return a.color;
  switch (a.severity) {
    case "critical":
      return "#ef4444";
    case "warning":
      return "#f59e0b";
    default:
      return "#fbbf24";
  }
}
