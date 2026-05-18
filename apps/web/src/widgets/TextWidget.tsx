import { cn } from "@/lib/utils";

/**
 * Text / heading / divider widgets — no data fetch, no query.
 * Used as structural elements inside a dashboard: section labels,
 * markdown notes, visual separators between data widgets.
 *
 * Variants live as separate widget.type values so the picker can show
 * three distinct icons without inventing a config field for variant.
 */

export function HeadingWidget({
  text,
  level = "h2",
}: {
  text: string;
  level?: "h1" | "h2" | "h3";
}) {
  const size =
    level === "h1" ? "text-2xl" : level === "h2" ? "text-lg" : "text-sm";
  return (
    <div className="flex items-center h-full px-1">
      <span className={cn("font-display text-foreground", size)}>
        {text || "Heading"}
      </span>
    </div>
  );
}

export function TextWidget({ text }: { text: string }) {
  // Simple markdown-ish: respect newlines, bold via **x**, code via `x`.
  // Intentionally minimal — operators wanting full markdown can use a
  // custom plugin component.
  const formatted = (text || "").split("\n").map((line, i) => {
    const parts = line.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
    return (
      <p key={i} className="text-sm text-muted-foreground font-body leading-relaxed">
        {parts.map((p, j) => {
          if (p.startsWith("**") && p.endsWith("**")) {
            return (
              <strong key={j} className="text-foreground font-semibold">
                {p.slice(2, -2)}
              </strong>
            );
          }
          if (p.startsWith("`") && p.endsWith("`")) {
            return (
              <code key={j} className="font-mono-deck text-foreground bg-secondary/40 px-1 rounded text-xs">
                {p.slice(1, -1)}
              </code>
            );
          }
          return <span key={j}>{p}</span>;
        })}
      </p>
    );
  });
  return (
    <div className="h-full px-1 py-1 overflow-auto">
      {formatted.length > 0 ? formatted : (
        <p className="text-sm text-muted-foreground/60 italic">Empty text widget</p>
      )}
    </div>
  );
}

export function DividerWidget() {
  return (
    <div className="flex items-center h-full px-1">
      <div className="flex-1 h-px bg-border" />
    </div>
  );
}
