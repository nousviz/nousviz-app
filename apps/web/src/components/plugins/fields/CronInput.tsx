/**
 * CronInput — `type: cron` field renderer (P120, v0.8.6).
 *
 * Text input with a human-readable preview. Uses Option B (known-patterns
 * lookup) to avoid pulling in a cron parser dependency. Patterns outside
 * the known map show as "Advanced: <raw expression>" — honest, doesn't
 * pretend to understand exotic cron.
 */

import { Clock } from "lucide-react";

interface Props {
  name: string;
  value: string;
  onChange: (next: string) => void;
  required?: boolean;
}

// Mirrors _SCHEDULE_LABELS in apps/api/src/routes/jobs.py.
const SCHEDULE_LABELS: Record<string, string> = {
  "*/5 * * * *": "Every 5 minutes",
  "*/10 * * * *": "Every 10 minutes",
  "*/15 * * * *": "Every 15 minutes",
  "*/30 * * * *": "Every 30 minutes",
  "0 * * * *": "Every hour",
  "0 */2 * * *": "Every 2 hours",
  "0 */4 * * *": "Every 4 hours",
  "0 */6 * * *": "Every 6 hours",
  "0 */12 * * *": "Every 12 hours",
  "0 6 * * *": "Daily at 6:00 AM",
  "0 0 * * *": "Daily at midnight",
  "0 0 * * 1": "Weekly (Monday)",
};

const PRESETS: { label: string; value: string }[] = [
  { label: "Every hour", value: "0 * * * *" },
  { label: "Every 6 hours", value: "0 */6 * * *" },
  { label: "Daily at 6am", value: "0 6 * * *" },
  { label: "Daily at midnight", value: "0 0 * * *" },
  { label: "Weekly (Monday)", value: "0 0 * * 1" },
];

const CRON_FIELD_RE = /^(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)$/;

function describe(expr: string): { level: "ok" | "advanced" | "invalid"; text: string } {
  const trimmed = expr.trim();
  if (!trimmed) return { level: "advanced", text: "No schedule set" };
  const label = SCHEDULE_LABELS[trimmed];
  if (label) return { level: "ok", text: label };
  if (!CRON_FIELD_RE.test(trimmed)) {
    return { level: "invalid", text: `Invalid cron expression: ${trimmed}` };
  }
  return { level: "advanced", text: `Advanced: ${trimmed}` };
}

export default function CronInput({ name, value, onChange, required }: Props) {
  const preview = describe(value);

  return (
    <div className="space-y-1.5">
      <input
        name={name}
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="0 */6 * * *"
        required={required}
        className="h-8 px-3 rounded-md bg-background border border-border text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary w-full sm:w-56 font-mono-deck"
      />
      <p
        className={
          preview.level === "invalid"
            ? "text-[11px] text-red-400 inline-flex items-center gap-1"
            : preview.level === "advanced"
            ? "text-[11px] text-muted-foreground inline-flex items-center gap-1"
            : "text-[11px] text-emerald-400 inline-flex items-center gap-1"
        }
      >
        <Clock className="w-3 h-3" /> {preview.text}
      </p>
      <div className="flex flex-wrap gap-1.5">
        {PRESETS.map((p) => (
          <button
            key={p.value}
            type="button"
            onClick={() => onChange(p.value)}
            className="text-[10px] px-2 py-0.5 rounded-full bg-secondary text-muted-foreground hover:text-foreground hover:bg-secondary/80 transition-colors"
          >
            {p.label}
          </button>
        ))}
      </div>
    </div>
  );
}
