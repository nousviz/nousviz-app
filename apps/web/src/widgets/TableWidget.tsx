import { cn } from "@/lib/utils";
import { useCompactNumbers, fmtNumber } from "@/hooks/useCompactNumbers";

interface Column {
  field: string;
  label: string;
  format?: "currency" | "number" | "percent";
  align?: "left" | "right";
}

interface TableWidgetProps {
  title?: string;
  columns: Column[];
  rows: Record<string, unknown>[];
  loading?: boolean;
}

function formatCell(value: unknown, format?: string, compact?: boolean): string {
  if (value == null) return "—";
  const num = typeof value === "number" ? value : Number(value);
  if (isNaN(num) && typeof value === "string") return value;
  if (compact) return fmtNumber(num, true, format);
  switch (format) {
    case "currency":
      return `$${num.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
    case "percent":
      return `${num.toFixed(1)}%`;
    case "number":
      return num.toLocaleString();
    default:
      return String(value);
  }
}

export default function TableWidget({ title, columns, rows, loading }: TableWidgetProps) {
  const { compact } = useCompactNumbers();
  if (loading) {
    return (
      <div className="bg-card rounded-lg border border-border overflow-hidden animate-pulse">
        {title && <div className="p-4 border-b border-border"><div className="h-4 w-32 bg-secondary rounded" /></div>}
        <div className="p-4 space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-4 bg-secondary rounded" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-card rounded-lg border border-border overflow-hidden">
      {title && (
        <div className="p-4 border-b border-border">
          <h3 className="font-display text-sm text-foreground">{title}</h3>
        </div>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              {columns.map((col) => (
                <th
                  key={col.field}
                  className={cn(
                    "px-4 py-2.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider",
                    col.format === "currency" || col.format === "number" || col.format === "percent" || col.align === "right"
                      ? "text-right"
                      : "text-left"
                  )}
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.map((row, i) => (
              <tr key={i} className="hover:bg-secondary/30 transition-colors">
                {columns.map((col) => (
                  <td
                    key={col.field}
                    className={cn(
                      "px-4 py-2.5",
                      col.format === "currency" || col.format === "number" || col.format === "percent" || col.align === "right"
                        ? "text-right font-mono-deck text-foreground"
                        : "text-foreground font-body"
                    )}
                  >
                    {formatCell(row[col.field], col.format, compact)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && (
          <div className="p-8 text-center text-sm text-muted-foreground">No data</div>
        )}
      </div>
    </div>
  );
}
