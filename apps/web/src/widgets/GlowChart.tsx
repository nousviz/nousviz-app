import { useState, useMemo } from "react";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { cn } from "@/lib/utils";

// ── Types ────────────────────────────────────────────────────────────

export interface GlowChartProps {
  data: Record<string, any>[];
  xKey: string;
  metrics: {
    key: string;
    label: string;
    color: string;
    defaultOn?: boolean;
  }[];
  title?: string;
  periodOptions?: { label: string; value: string }[];
  onPeriodChange?: (period: string) => void;
  activePeriod?: string;
  granularityOptions?: string[];
  activeGranularity?: string;
  onGranularityChange?: (g: string) => void;
  formatX?: (val: string) => string;
  formatY?: (val: number) => string;
  height?: number;
}

// ── Helpers ──────────────────────────────────────────────────────────

function defaultFormatY(v: number): string {
  if (Math.abs(v) >= 1_000_000) return (v / 1_000_000).toFixed(1) + "M";
  if (Math.abs(v) >= 1_000) return (v / 1_000).toFixed(0) + "K";
  return v.toLocaleString();
}

function defaultFormatX(v: string): string {
  if (!v) return v;
  // Try to format as "Mon YYYY"
  try {
    const d = new Date(v);
    if (!isNaN(d.getTime())) {
      return d.toLocaleDateString("en-US", { month: "short", year: "numeric" });
    }
  } catch {}
  return v.slice(0, 7);
}

// ── Component ────────────────────────────────────────────────────────

export default function GlowChart({
  data,
  xKey,
  metrics,
  title,
  periodOptions,
  onPeriodChange,
  activePeriod,
  granularityOptions,
  activeGranularity,
  onGranularityChange,
  formatX = defaultFormatX,
  formatY = defaultFormatY,
  height = 320,
}: GlowChartProps) {
  const [activeMetrics] = useState<Set<string>>(() =>
    new Set(metrics.filter(m => m.defaultOn !== false).map(m => m.key))
  );


  const visibleMetrics = metrics.filter(m => activeMetrics.has(m.key));

  // Calculate KPI summaries from visible data
  const summaries = useMemo(() => {
    return metrics.map(m => {
      const vals = data.map(d => Number(d[m.key]) || 0).filter(v => v !== 0);
      const sum = vals.reduce((a, b) => a + b, 0);
      const avg = vals.length > 0 ? sum / vals.length : 0;
      const last = vals.length > 0 ? vals[vals.length - 1] : 0;
      const prev = vals.length > 1 ? vals[vals.length - 2] : last;
      const change = prev !== 0 ? ((last - prev) / Math.abs(prev)) * 100 : 0;
      return { ...m, sum, avg, last, change };
    });
  }, [data, metrics]);

  return (
    <div className="space-y-0">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        {title && <h3 className="text-sm font-display font-semibold text-foreground">{title}</h3>}
        <div className="flex items-center gap-2">
          {/* Period selector */}
          {periodOptions && (
            <div className="flex gap-1 bg-secondary/50 rounded-lg p-0.5">
              {periodOptions.map(p => (
                <button
                  key={p.value}
                  onClick={() => onPeriodChange?.(p.value)}
                  className={cn(
                    "px-3 py-1 rounded-md text-[10px] font-mono uppercase tracking-wider transition-colors",
                    activePeriod === p.value
                      ? "bg-card text-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  {p.label}
                </button>
              ))}
            </div>
          )}
          {/* Granularity */}
          {granularityOptions && (
            <div className="flex gap-1 bg-secondary/50 rounded-lg p-0.5">
              {granularityOptions.map(g => (
                <button
                  key={g}
                  onClick={() => onGranularityChange?.(g)}
                  className={cn(
                    "px-2.5 py-1 rounded-md text-[10px] font-mono capitalize transition-colors",
                    activeGranularity === g
                      ? "bg-card text-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  {g}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Metric toggles */}
      <div className="flex flex-wrap gap-x-5 gap-y-2 mb-5">
        {metrics.map(m => {
          const active = activeMetrics.has(m.key);
          return (
            <label key={m.key} className="flex items-center gap-2 cursor-pointer select-none group">
              <div className={cn(
                "w-4 h-4 rounded border-2 flex items-center justify-center transition-all",
                active
                  ? "border-transparent"
                  : "border-muted-foreground/30 group-hover:border-muted-foreground/50"
              )} style={active ? { backgroundColor: m.color, boxShadow: `0 0 8px ${m.color}40` } : {}}>
                {active && (
                  <svg className="w-2.5 h-2.5 text-white" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M2 6l3 3 5-5" />
                  </svg>
                )}
              </div>
              <span className={cn(
                "text-xs transition-colors",
                active ? "text-foreground" : "text-muted-foreground group-hover:text-foreground"
              )}>
                {m.label}
              </span>
            </label>
          );
        })}
      </div>

      {/* Chart */}
      <div className="relative" style={{ height }}>
        {/* Glow backdrop */}
        <div className="absolute inset-0 rounded-xl overflow-hidden">
          <div className="absolute bottom-0 left-0 right-0 h-[60%] bg-gradient-to-t from-[hsl(var(--card))]/80 to-transparent" />
        </div>

        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <defs>
              {metrics.map(m => (
                <linearGradient key={`grad-${m.key}`} id={`glow-${m.key}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={m.color} stopOpacity={0.4} />
                  <stop offset="60%" stopColor={m.color} stopOpacity={0.08} />
                  <stop offset="100%" stopColor={m.color} stopOpacity={0} />
                </linearGradient>
              ))}
              {/* Glow filter */}
              <filter id="glowFilter">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="hsl(var(--border))"
              strokeOpacity={0.4}
              vertical={false}
            />
            <XAxis
              dataKey={xKey}
              tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))", fontFamily: "var(--font-mono-deck)" }}
              tickFormatter={formatX}
              axisLine={{ stroke: "hsl(var(--border))", strokeOpacity: 0.5 }}
              tickLine={false}
              dy={8}
            />
            <YAxis
              tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))", fontFamily: "var(--font-mono-deck)" }}
              tickFormatter={formatY}
              axisLine={false}
              tickLine={false}
              dx={-4}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: 10,
                fontSize: 11,
                fontFamily: "var(--font-mono-deck)",
                boxShadow: "0 8px 32px rgba(0,0,0,0.3)",
              }}
              labelFormatter={formatX}
              formatter={(value: number, name: string) => {
                const m = metrics.find(mm => mm.key === name);
                return [formatY(value), m?.label || name];
              }}
            />
            {visibleMetrics.map(m => (
              <Area
                key={m.key}
                type="monotone"
                dataKey={m.key}
                stroke={m.color}
                strokeWidth={2.5}
                fill={`url(#glow-${m.key})`}
                dot={{ r: 3, fill: m.color, stroke: m.color, strokeWidth: 1, filter: "url(#glowFilter)" }}
                activeDot={{ r: 5, fill: m.color, stroke: "#fff", strokeWidth: 2, filter: "url(#glowFilter)" }}
                name={m.key}
                animationDuration={800}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>

        {/* 3D perspective base */}
        <div className="absolute bottom-0 left-8 right-2 h-8 -mb-2"
          style={{
            background: "linear-gradient(180deg, rgba(100,150,255,0.06) 0%, transparent 100%)",
            transform: "perspective(400px) rotateX(30deg)",
            transformOrigin: "top center",
            borderTop: "1px solid rgba(100,180,255,0.15)",
          }}
        />
      </div>

      {/* Summary cards */}
      {summaries.filter(s => activeMetrics.has(s.key)).length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-6">
          {summaries.filter(s => activeMetrics.has(s.key)).map(s => (
            <div key={s.key} className="bg-card/50 rounded-lg border border-border/50 p-3">
              <div className="flex items-center gap-2 mb-1.5">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: s.color, boxShadow: `0 0 6px ${s.color}60` }} />
                <span className="text-[10px] text-muted-foreground uppercase tracking-wider">{s.label}</span>
              </div>
              <p className="text-lg font-display font-bold">{formatY(s.last)}</p>
              <p className={cn("text-[10px] font-mono",
                s.change > 0 ? "text-emerald-400" : s.change < 0 ? "text-red-400" : "text-muted-foreground"
              )}>
                {s.change > 0 ? "▲" : s.change < 0 ? "▼" : "→"} {Math.abs(s.change).toFixed(1)}% vs prior
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
