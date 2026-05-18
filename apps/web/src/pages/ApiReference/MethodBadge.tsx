import type { HttpMethod } from "./types";

const STYLES: Record<HttpMethod, string> = {
  get: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  post: "bg-sky-500/15 text-sky-400 border-sky-500/30",
  put: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  patch: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  delete: "bg-rose-500/15 text-rose-400 border-rose-500/30",
};

export default function MethodBadge({ method, size = "sm" }: { method: HttpMethod; size?: "sm" | "xs" }) {
  const cls = STYLES[method] ?? "bg-secondary text-muted-foreground border-border";
  const sizeCls =
    size === "xs"
      ? "text-[10px] px-1.5 py-0.5 min-w-[42px]"
      : "text-xs px-2 py-0.5 min-w-[52px]";
  return (
    <span
      className={`inline-flex items-center justify-center rounded border font-mono-deck font-medium uppercase tracking-wide ${sizeCls} ${cls}`}
    >
      {method}
    </span>
  );
}
