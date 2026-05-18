/**
 * FilterChips — column-level filter UI for the dataset row viewer (B262).
 *
 * Renders the active filters as removable chips above the table, plus an
 * "+ Add filter" button that opens a popover for creating a new filter.
 * The popover offers type-aware operator suggestions: text columns get
 * contains/startswith/eq, numeric/date columns get comparison ops,
 * nullable columns surface is_null/not_null.
 *
 * The component is purely presentational — it owns the popover state but
 * lifts the filter list to the parent via onChange. Filters are
 * serialized to / from `?filter=col:op:value` URL params by the parent.
 */

import { useEffect, useRef, useState } from "react";
import { Plus, X } from "lucide-react";
import { cn } from "@/lib/utils";

// ── Types ────────────────────────────────────────────────────────────

export type FilterOp =
  | "eq"
  | "neq"
  | "gt"
  | "lt"
  | "gte"
  | "lte"
  | "contains"
  | "startswith"
  | "is_null"
  | "not_null";

export interface Filter {
  col: string;
  op: FilterOp;
  value?: string; // omitted for is_null / not_null
}

export interface FilterChipsColumn {
  name: string;
  data_type: string;
  is_nullable?: boolean;
}

interface FilterChipsProps {
  columns: FilterChipsColumn[];
  filters: Filter[];
  onChange: (filters: Filter[]) => void;
  maxFilters?: number;
}

// ── Operator metadata ────────────────────────────────────────────────

const OP_LABEL: Record<FilterOp, string> = {
  eq: "=",
  neq: "≠",
  gt: ">",
  lt: "<",
  gte: "≥",
  lte: "≤",
  contains: "contains",
  startswith: "starts with",
  is_null: "is empty",
  not_null: "is not empty",
};

const TEXT_TYPES = new Set([
  "text",
  "character varying",
  "varchar",
  "character",
  "char",
  "json",
  "jsonb",
  "uuid",
]);

const NUMERIC_TYPES = new Set([
  "smallint",
  "integer",
  "bigint",
  "decimal",
  "numeric",
  "real",
  "double precision",
  "money",
]);

const DATE_TYPES = new Set([
  "date",
  "timestamp",
  "timestamp without time zone",
  "timestamp with time zone",
  "time",
  "time without time zone",
  "time with time zone",
]);

const BOOLEAN_TYPES = new Set(["boolean"]);

function opsFor(column: FilterChipsColumn): FilterOp[] {
  const t = column.data_type;
  const ops: FilterOp[] = [];

  if (TEXT_TYPES.has(t)) {
    ops.push("contains", "startswith", "eq", "neq");
  } else if (NUMERIC_TYPES.has(t)) {
    ops.push("eq", "neq", "gt", "lt", "gte", "lte");
  } else if (DATE_TYPES.has(t)) {
    ops.push("gte", "lte", "eq", "neq", "gt", "lt");
  } else if (BOOLEAN_TYPES.has(t)) {
    ops.push("eq", "neq");
  } else {
    // Unknown type — fall back to eq/neq + null checks
    ops.push("eq", "neq");
  }

  if (column.is_nullable !== false) {
    ops.push("is_null", "not_null");
  }

  return ops;
}

function inputTypeFor(column: FilterChipsColumn): "text" | "number" | "date" | "datetime-local" {
  const t = column.data_type;
  if (NUMERIC_TYPES.has(t)) return "number";
  if (t === "date") return "date";
  if (DATE_TYPES.has(t)) return "datetime-local";
  return "text";
}

// ── Component ────────────────────────────────────────────────────────

export function FilterChips({
  columns,
  filters,
  onChange,
  maxFilters = 8,
}: FilterChipsProps) {
  const [popoverOpen, setPopoverOpen] = useState(false);
  const [draftCol, setDraftCol] = useState<string>("");
  const [draftOp, setDraftOp] = useState<FilterOp>("eq");
  const [draftValue, setDraftValue] = useState<string>("");
  const popoverRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  const atCap = filters.length >= maxFilters;

  // Reset draft when popover opens/closes; default column to first.
  useEffect(() => {
    if (popoverOpen) {
      const firstCol = columns[0]?.name ?? "";
      setDraftCol(firstCol);
      const firstColMeta = columns.find((c) => c.name === firstCol);
      const firstOp = firstColMeta ? opsFor(firstColMeta)[0] : "eq";
      setDraftOp(firstOp);
      setDraftValue("");
    }
  }, [popoverOpen, columns]);

  // Click-outside to close popover.
  useEffect(() => {
    if (!popoverOpen) return;
    function onClick(e: MouseEvent) {
      const target = e.target as Node;
      if (
        popoverRef.current &&
        !popoverRef.current.contains(target) &&
        buttonRef.current &&
        !buttonRef.current.contains(target)
      ) {
        setPopoverOpen(false);
      }
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [popoverOpen]);

  // When the user picks a different column, reset the op to the first
  // op valid for that column's type.
  useEffect(() => {
    if (!draftCol) return;
    const col = columns.find((c) => c.name === draftCol);
    if (!col) return;
    const validOps = opsFor(col);
    if (!validOps.includes(draftOp)) {
      setDraftOp(validOps[0]);
    }
  }, [draftCol, columns, draftOp]);

  function removeFilter(idx: number) {
    onChange(filters.filter((_, i) => i !== idx));
  }

  function addFilter() {
    if (!draftCol || !draftOp) return;
    const isNullOp = draftOp === "is_null" || draftOp === "not_null";
    if (!isNullOp && !draftValue.trim()) return;
    const next: Filter = isNullOp
      ? { col: draftCol, op: draftOp }
      : { col: draftCol, op: draftOp, value: draftValue };
    onChange([...filters, next]);
    setPopoverOpen(false);
  }

  const draftColMeta = columns.find((c) => c.name === draftCol);
  const draftOps = draftColMeta ? opsFor(draftColMeta) : [];
  const isDraftNullOp = draftOp === "is_null" || draftOp === "not_null";

  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      {filters.map((f, idx) => (
        <span
          key={idx}
          className="inline-flex items-center gap-1 h-7 pl-2 pr-1 rounded-md bg-secondary border border-border text-xs text-foreground"
        >
          <span className="font-mono-deck text-muted-foreground">{f.col}</span>
          <span className="text-muted-foreground">{OP_LABEL[f.op]}</span>
          {f.value !== undefined && (
            <span className="font-mono-deck">{f.value}</span>
          )}
          <button
            type="button"
            onClick={() => removeFilter(idx)}
            className="ml-0.5 h-5 w-5 rounded hover:bg-background flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
            title="Remove filter"
          >
            <X className="w-3 h-3" />
          </button>
        </span>
      ))}

      <div className="relative">
        <button
          ref={buttonRef}
          type="button"
          onClick={() => setPopoverOpen((v) => !v)}
          disabled={atCap}
          className={cn(
            "h-7 px-2 rounded-md bg-secondary border border-border text-xs text-muted-foreground hover:text-foreground inline-flex items-center gap-1 transition-colors",
            atCap && "opacity-40 cursor-not-allowed",
          )}
          title={atCap ? `Filter limit reached (max ${maxFilters})` : "Add filter"}
        >
          <Plus className="w-3 h-3" />
          {filters.length === 0 ? "Add filter" : "Filter"}
        </button>

        {popoverOpen && (
          <div
            ref={popoverRef}
            className="absolute z-30 left-0 mt-1 w-72 rounded-lg bg-card border border-border shadow-lg p-3 space-y-2"
          >
            <label className="block">
              <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                Column
              </span>
              <select
                value={draftCol}
                onChange={(e) => setDraftCol(e.target.value)}
                className="mt-1 w-full h-8 px-2 rounded bg-secondary border border-border text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              >
                {columns.map((c) => (
                  <option key={c.name} value={c.name}>
                    {c.name} <span className="opacity-60">({c.data_type})</span>
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                Operator
              </span>
              <select
                value={draftOp}
                onChange={(e) => setDraftOp(e.target.value as FilterOp)}
                className="mt-1 w-full h-8 px-2 rounded bg-secondary border border-border text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              >
                {draftOps.map((op) => (
                  <option key={op} value={op}>
                    {OP_LABEL[op]}
                  </option>
                ))}
              </select>
            </label>

            {!isDraftNullOp && (
              <label className="block">
                <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                  Value
                </span>
                <input
                  type={draftColMeta ? inputTypeFor(draftColMeta) : "text"}
                  value={draftValue}
                  onChange={(e) => setDraftValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      addFilter();
                    }
                  }}
                  className="mt-1 w-full h-8 px-2 rounded bg-secondary border border-border text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  autoFocus
                />
              </label>
            )}

            <div className="flex items-center justify-end gap-2 pt-1">
              <button
                type="button"
                onClick={() => setPopoverOpen(false)}
                className="h-7 px-3 rounded text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={addFilter}
                disabled={!isDraftNullOp && !draftValue.trim()}
                className="h-7 px-3 rounded bg-primary text-primary-foreground text-xs hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-opacity"
              >
                Add
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── URL serialization helpers ────────────────────────────────────────

/**
 * Serialize a Filter to its `col:op:value` URL form. Null ops omit the
 * value (and the trailing colon).
 */
export function serializeFilter(f: Filter): string {
  if (f.op === "is_null" || f.op === "not_null") {
    return `${f.col}:${f.op}`;
  }
  return `${f.col}:${f.op}:${f.value ?? ""}`;
}

/**
 * Parse a `col:op:value` URL form into a Filter. Returns null on
 * malformed input (caller decides whether to drop or surface).
 */
export function parseFilter(raw: string): Filter | null {
  if (!raw || !raw.includes(":")) return null;

  // indexOf-based split so values containing colons (timestamps, URLs)
  // survive the round-trip.
  const firstColon = raw.indexOf(":");
  const secondColon = raw.indexOf(":", firstColon + 1);

  const col = raw.slice(0, firstColon);
  const op = secondColon === -1 ? raw.slice(firstColon + 1) : raw.slice(firstColon + 1, secondColon);
  const value = secondColon === -1 ? undefined : raw.slice(secondColon + 1);

  if (!col || !op) return null;

  const validOps: FilterOp[] = [
    "eq", "neq", "gt", "lt", "gte", "lte",
    "contains", "startswith", "is_null", "not_null",
  ];
  if (!validOps.includes(op as FilterOp)) return null;

  if (op === "is_null" || op === "not_null") {
    return { col, op: op as FilterOp };
  }
  if (value === undefined) return null;
  return { col, op: op as FilterOp, value };
}
