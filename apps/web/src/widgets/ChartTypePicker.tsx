import { BarChart3, TrendingUp, Hash, Table2, Component, Type, Heading, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Visual chart-type picker. Replaces a `<select>` in the widget config
 * panel with a row of icon tiles. Operator picks by recognising the
 * shape, not by reading text from a dropdown.
 */

export interface ChartTypeOption {
  type: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  /** Truthy = data widget (needs a query); falsy = layout/text widget. */
  needsQuery?: boolean;
}

export const CHART_TYPE_OPTIONS: ChartTypeOption[] = [
  { type: "kpi", label: "KPI", icon: Hash, needsQuery: true },
  { type: "line_chart", label: "Line", icon: TrendingUp, needsQuery: true },
  { type: "bar_chart", label: "Bar", icon: BarChart3, needsQuery: true },
  { type: "stacked_bar_chart", label: "Stacked", icon: BarChart3, needsQuery: true },
  { type: "table", label: "Table", icon: Table2, needsQuery: true },
  { type: "heading", label: "Heading", icon: Heading },
  { type: "text", label: "Text", icon: Type },
  { type: "divider", label: "Divider", icon: Minus },
  { type: "custom", label: "Custom", icon: Component },
];

export function ChartTypePicker({
  value,
  onChange,
}: {
  value: string;
  onChange: (type: string) => void;
}) {
  return (
    <div className="grid grid-cols-3 gap-1.5">
      {CHART_TYPE_OPTIONS.map((opt) => {
        const Icon = opt.icon;
        const active = opt.type === value;
        return (
          <button
            key={opt.type}
            type="button"
            onClick={() => onChange(opt.type)}
            className={cn(
              "flex flex-col items-center justify-center gap-1 px-2 py-2 rounded-md border transition-colors",
              active
                ? "bg-primary/10 border-primary/40 text-primary"
                : "bg-card border-border text-muted-foreground hover:text-foreground hover:border-primary/30",
            )}
            title={opt.label}
          >
            <Icon className="w-4 h-4" />
            <span className="text-[10px] font-mono-deck">{opt.label}</span>
          </button>
        );
      })}
    </div>
  );
}
