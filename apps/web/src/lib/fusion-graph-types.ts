/**
 * FusionGraph types — the source of truth for the visual fusion builder
 * (B263 / v0.9.11.7).
 *
 * Shared between the compiler (`fusion-compiler.ts`), the builder UI
 * (`widgets/FusionBuilder.tsx`), and round-trip serialization stored
 * in the fusion widget JSONB alongside `query` + `params`.
 */

export type JoinKind = "inner" | "left" | "right" | "full";

export type AggregationFn =
  | "sum"
  | "avg"
  | "min"
  | "max"
  | "count"
  | "count_distinct";

/**
 * Filter operator set — reused from B262's row-endpoint filter chips.
 * Adding a new op requires updating both this type and the compiler's
 * `_OP_TO_SQL` map.
 */
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

/**
 * One source in the fusion graph. The alias is auto-assigned by the
 * builder (s1, s2, …) and is referenced by joins/filters/groupBy.
 */
export interface SourceRef {
  alias: string; // s1, s2, ... — must match /^s[0-9]+$/
  pluginId: string; // "fusions" for published fusions, plugin slug otherwise
  table: string; // table name (in `public`) or view name (in `fusions`)
}

/**
 * A join between two sources. Single-equality predicate per join row;
 * multi-predicate joins are expressed as multiple rows with the same
 * (leftAlias, rightAlias) — the compiler ANDs them together.
 */
export interface JoinRef {
  kind: JoinKind;
  leftAlias: string;
  rightAlias: string;
  on: { leftCol: string; rightCol: string };
}

/**
 * A WHERE-clause predicate. AND-combined at the top level (OR groups
 * deferred to a future polish release per B263 scope decision).
 */
export interface FilterRef {
  alias: string;
  col: string;
  op: FilterOp;
  value?: string; // omitted for is_null / not_null
}

/**
 * GROUP BY clause: zero or more grouping columns + zero or more
 * aggregations. When non-null, the SELECT clause emits `<group cols>,
 * <aggregations>` instead of the default `<alias>.*`.
 */
export interface GroupByRef {
  cols: { alias: string; col: string }[];
  aggregations: {
    fn: AggregationFn;
    alias?: string; // omitted for count(*)
    col?: string; // omitted for count(*)
    outputName: string; // user-named output column; must match /^[a-zA-Z_][a-zA-Z0-9_]*$/
  }[];
}

/**
 * ORDER BY clause. `col` is either an output name (when groupBy is
 * set) or `<alias>.<col>` form (no groupBy).
 */
export interface OrderByRef {
  col: string;
  direction: "asc" | "desc";
}

export interface FusionGraph {
  sources: SourceRef[];
  joins: JoinRef[];
  filters: FilterRef[]; // AND-combined
  groupBy: GroupByRef | null;
  orderBy: OrderByRef | null;
  limit: number | null;
}

export const EMPTY_GRAPH: FusionGraph = {
  sources: [],
  joins: [],
  filters: [],
  groupBy: null,
  orderBy: null,
  limit: null,
};

// Caps + validation constants used by the compiler and the builder UI.
export const MAX_SOURCES = 4;
export const MAX_JOINS = 4;
export const MAX_FILTERS = 8;
export const MAX_AGGREGATIONS = 8;
export const MAX_LIMIT = 10000;

// Identifier-safety regexes — must match the backend `_VALID_IDENT`
// semantics in apps/api/src/catalog.py.
export const VALID_IDENTIFIER = /^[a-zA-Z_][a-zA-Z0-9_]*$/;
export const VALID_ALIAS = /^s[0-9]+$/;
