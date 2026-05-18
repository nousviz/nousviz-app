import { createContext, useContext, useState, useCallback, useMemo } from "react";

// ── Types ────────────────────────────────────────────────────────────

export type NumberFormat = "compact" | "full" | "inherit";

interface CompactNumbersCtx {
  /** System-wide default */
  systemCompact: boolean;
  /** Toggle system-wide default */
  toggle: () => void;
  /** Resolve the effective compact state given an override */
  isCompact: (override?: NumberFormat) => boolean;
  /** The raw system setting for display */
  compact: boolean;
}

// ── Context ──────────────────────────────────────────────────────────

const CompactNumbersContext = createContext<CompactNumbersCtx>({
  systemCompact: false,
  toggle: () => {},
  isCompact: () => false,
  compact: false,
});

/**
 * Override provider — wraps a subtree to force compact/full regardless of system setting.
 * Used by plugins/dashboards that need a specific number format.
 */
export function NumberFormatOverride({ format, children }: { format?: NumberFormat; children: React.ReactNode }) {
  const parent = useContext(CompactNumbersContext);
  if (!format || format === "inherit") return <>{children}</>;

  const overridden: CompactNumbersCtx = {
    ...parent,
    systemCompact: format === "compact",
    compact: format === "compact",
    isCompact: () => format === "compact",
  };

  return (
    <CompactNumbersContext.Provider value={overridden}>
      {children}
    </CompactNumbersContext.Provider>
  );
}

export function CompactNumbersProvider({ children }: { children: React.ReactNode }) {
  const [systemCompact, setSystemCompact] = useState(() => {
    return localStorage.getItem("nousviz_compact_numbers") === "true";
  });

  const toggle = useCallback(() => {
    setSystemCompact(prev => {
      const next = !prev;
      localStorage.setItem("nousviz_compact_numbers", String(next));
      return next;
    });
  }, []);

  const isCompact = useCallback((override?: NumberFormat) => {
    if (override === "compact") return true;
    if (override === "full") return false;
    return systemCompact; // "inherit" or undefined
  }, [systemCompact]);

  const value = useMemo(() => ({
    systemCompact,
    toggle,
    isCompact,
    compact: systemCompact,
  }), [systemCompact, toggle, isCompact]);

  return (
    <CompactNumbersContext.Provider value={value}>
      {children}
    </CompactNumbersContext.Provider>
  );
}

export function useCompactNumbers(override?: NumberFormat) {
  const ctx = useContext(CompactNumbersContext);
  const compact = ctx.isCompact(override);
  return { ...ctx, compact };
}

// ── Formatter ────────────────────────────────────────────────────────

/**
 * Format a number — compact (1.2M, 45.3K) or full (1,234,567)
 */
export function fmtNumber(value: number, compact: boolean, format?: string): string {
  if (format === "percent") return `${value.toFixed(1)}%`;

  const sign = value < 0 ? "-" : "";
  const abs = Math.abs(value);

  if (compact) {
    const prefix = format === "currency" ? "$" : "";
    if (abs >= 1_000_000_000) return sign + prefix + (abs / 1_000_000_000).toFixed(2) + "B";
    if (abs >= 1_000_000) return sign + prefix + (abs / 1_000_000).toFixed(2) + "M";
    if (abs >= 1_000) return sign + prefix + (abs / 1_000).toFixed(1) + "K";
    if (format === "currency") return sign + prefix + abs.toFixed(2);
    return value.toLocaleString();
  }

  switch (format) {
    case "currency":
      return sign + "$" + abs.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    case "number":
    default:
      return value.toLocaleString();
  }
}
