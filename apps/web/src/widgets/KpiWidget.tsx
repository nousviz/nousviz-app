import { ArrowUpRight, ArrowDownRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { useCompactNumbers, fmtNumber } from "@/hooks/useCompactNumbers";

interface KpiWidgetProps {
  label: string;
  value: string | number;
  change?: number | null;
  format?: "currency" | "number" | "percent";
  loading?: boolean;
}

export default function KpiWidget({ label, value, change, format, loading }: KpiWidgetProps) {
  const { compact } = useCompactNumbers();

  function formatValue(v: string | number): string {
    if (typeof v === "string") {
      // Try parsing as number for compact formatting
      const num = Number(v);
      if (!isNaN(num) && compact) return fmtNumber(num, true, format);
      return v;
    }
    return fmtNumber(v, compact, format);
  }

  if (loading) {
    return (
      <div className="bg-card rounded-lg border border-border p-4 animate-pulse">
        <div className="h-3 w-20 bg-secondary rounded mb-3" />
        <div className="h-7 w-24 bg-secondary rounded" />
      </div>
    );
  }

  return (
    <div className="bg-card rounded-lg border border-border p-4">
      <div className="flex items-center justify-between mb-1">
        <p className="text-xs text-muted-foreground font-body">{label}</p>
        {change != null && (
          <span
            className={cn(
              "text-xs font-mono-deck flex items-center gap-0.5",
              change > 0 ? "text-green-400" : change < 0 ? "text-red-400" : "text-muted-foreground"
            )}
          >
            {change > 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
            {Math.abs(change).toFixed(1)}%
          </span>
        )}
      </div>
      <p className="text-xl font-display text-foreground">{formatValue(value)}</p>
    </div>
  );
}
