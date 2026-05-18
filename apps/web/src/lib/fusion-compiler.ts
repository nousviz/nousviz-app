/**
 * fusion-compiler — compiles a FusionGraph into a parameterized SQL
 * SELECT statement that the existing fusion widget execution path can
 * run safely (B263 / v0.9.11.7).
 *
 * SECURITY MODEL
 * --------------
 * This module is the single trust boundary between user input (the
 * graph) and executable SQL. It MUST NOT interpolate user-supplied
 * strings into the SQL output as identifiers without strict regex
 * validation. Values become positional `$1, $2, …` placeholders that
 * psycopg2 escapes at execute time on the backend (B263 Phase 8).
 *
 * Identifier validation matches the backend's `_VALID_IDENT` regex so
 * a column name that's safe here is also safe when passed through to
 * Postgres. Operators come from a frozen mapping; aggregation
 * functions from a frozen list.
 */

import type {
  AggregationFn,
  FilterOp,
  FusionGraph,
  GroupByRef,
  JoinKind,
  OrderByRef,
} from "./fusion-graph-types";
import {
  MAX_AGGREGATIONS,
  MAX_FILTERS,
  MAX_JOINS,
  MAX_LIMIT,
  MAX_SOURCES,
  VALID_ALIAS,
  VALID_IDENTIFIER,
} from "./fusion-graph-types";

// ── Constants ────────────────────────────────────────────────────────

const JOIN_SQL: Record<JoinKind, string> = {
  inner: "INNER JOIN",
  left: "LEFT JOIN",
  right: "RIGHT JOIN",
  full: "FULL OUTER JOIN",
};

const OP_SQL: Record<FilterOp, string> = {
  eq: "=",
  neq: "<>",
  gt: ">",
  lt: "<",
  gte: ">=",
  lte: "<=",
  // contains / startswith use ILIKE with wrapped value
  contains: "ILIKE",
  startswith: "ILIKE",
  // is_null / not_null are rendered separately (no value, no operator slot)
  is_null: "IS NULL",
  not_null: "IS NOT NULL",
};

const AGG_FN_SQL: Record<AggregationFn, string> = {
  sum: "SUM",
  avg: "AVG",
  min: "MIN",
  max: "MAX",
  count: "COUNT",
  count_distinct: "COUNT",
};

// Plugin id reserved for published-fusion sources (B264). Tables referenced
// by sources with this pluginId are schema-qualified as `"fusions"."<name>"`.
const FUSIONS_PLUGIN_ID = "fusions";

// ── Schema cache shape (for column existence validation) ─────────────

export interface SchemaColumn {
  name: string;
  data_type?: string;
  is_nullable?: boolean;
}

export interface SchemaCacheLookup {
  /**
   * Return the columns for (pluginId, table), or null if unknown / not
   * loaded. The compiler treats null as "skip column existence checks
   * for this source" (loose mode — preview-time use). Production save
   * paths should pre-warm the cache so all sources resolve.
   */
  lookup(pluginId: string, table: string): SchemaColumn[] | null;
}

/** Convenience implementation backed by a plain Map. */
export class StaticSchemaCache implements SchemaCacheLookup {
  private map = new Map<string, SchemaColumn[]>();

  set(pluginId: string, table: string, cols: SchemaColumn[]): this {
    this.map.set(`${pluginId}::${table}`, cols);
    return this;
  }

  lookup(pluginId: string, table: string): SchemaColumn[] | null {
    return this.map.get(`${pluginId}::${table}`) ?? null;
  }
}

// ── Compile result ────────────────────────────────────────────────────

export interface CompileSuccess {
  ok: true;
  sql: string;
  params: unknown[]; // positional, matching $1, $2, …
}

export interface CompileFailure {
  ok: false;
  errors: string[];
}

export type CompileResult = CompileSuccess | CompileFailure;

// ── Identifier helpers ────────────────────────────────────────────────

function quoteIdent(name: string): string {
  // Caller has already validated against VALID_IDENTIFIER. Double-quote
  // wrap. Even the validated identifier is wrapped because Postgres
  // would otherwise lowercase unquoted identifiers and reject keywords.
  return `"${name}"`;
}

function qualified(pluginId: string, table: string): string {
  if (pluginId === FUSIONS_PLUGIN_ID) {
    return `${quoteIdent("fusions")}.${quoteIdent(table)}`;
  }
  // Plugin tables live in the public schema — schema-qualify to prevent
  // silent collisions when two plugins share a table name.
  return `${quoteIdent("public")}.${quoteIdent(table)}`;
}

// ── Validators ────────────────────────────────────────────────────────

function validateGraph(
  graph: FusionGraph,
  schemaCache: SchemaCacheLookup,
): string[] {
  const errs: string[] = [];

  // ── Sources ────────────────────────────────────────────────────────
  if (graph.sources.length === 0) {
    errs.push("must have at least one source");
    return errs; // everything downstream needs a source
  }
  if (graph.sources.length > MAX_SOURCES) {
    errs.push(`too many sources (max ${MAX_SOURCES})`);
  }

  const aliasSet = new Set<string>();
  const aliasToSource = new Map<
    string,
    { pluginId: string; table: string }
  >();

  for (const s of graph.sources) {
    if (!VALID_ALIAS.test(s.alias)) {
      errs.push(`invalid source alias ${JSON.stringify(s.alias)}; expected s1, s2, ...`);
      continue;
    }
    if (aliasSet.has(s.alias)) {
      errs.push(`duplicate source alias ${s.alias}`);
      continue;
    }
    if (!VALID_IDENTIFIER.test(s.table)) {
      errs.push(`Source ${JSON.stringify(s.table || "(empty)")}: invalid table name`);
      continue;
    }
    // v0.10.1.5: pluginId is metadata (used to pick schema + lookup cache)
    // NOT a SQL identifier — it's never interpolated into the output SQL.
    // The original VALID_IDENTIFIER check rejected plugin slugs with
    // hyphens (avizo-jira, cloudflare-analytics, etc.), blocking the
    // entire builder for the majority of installed plugins. Use a more
    // permissive regex that still rejects garbage.
    if (!/^[a-zA-Z0-9_.-]+$/.test(s.pluginId)) {
      errs.push(`Source ${JSON.stringify(s.table)}: plugin id ${JSON.stringify(s.pluginId)} is malformed`);
      continue;
    }
    aliasSet.add(s.alias);
    aliasToSource.set(s.alias, { pluginId: s.pluginId, table: s.table });
  }

  function colExists(alias: string, col: string): boolean | null {
    const src = aliasToSource.get(alias);
    if (!src) return false;
    const cols = schemaCache.lookup(src.pluginId, src.table);
    if (cols === null) return null; // schema not loaded — skip strict check
    return cols.some((c) => c.name === col);
  }

  // ── Joins ──────────────────────────────────────────────────────────
  if (graph.joins.length > MAX_JOINS) {
    errs.push(`too many joins (max ${MAX_JOINS})`);
  }
  for (let i = 0; i < graph.joins.length; i++) {
    const j = graph.joins[i];
    if (!aliasSet.has(j.leftAlias)) {
      errs.push(`join ${i + 1}: unknown left alias ${j.leftAlias}`);
    }
    if (!aliasSet.has(j.rightAlias)) {
      errs.push(`join ${i + 1}: unknown right alias ${j.rightAlias}`);
    }
    if (j.leftAlias === j.rightAlias) {
      errs.push(`join ${i + 1}: cannot join an alias to itself`);
    }
    if (!VALID_IDENTIFIER.test(j.on.leftCol)) {
      errs.push(`join ${i + 1}: invalid left column name ${JSON.stringify(j.on.leftCol)}`);
    }
    if (!VALID_IDENTIFIER.test(j.on.rightCol)) {
      errs.push(`join ${i + 1}: invalid right column name ${JSON.stringify(j.on.rightCol)}`);
    }
    if (aliasSet.has(j.leftAlias) && colExists(j.leftAlias, j.on.leftCol) === false) {
      errs.push(`join ${i + 1}: column ${j.on.leftCol} not in source ${j.leftAlias}`);
    }
    if (aliasSet.has(j.rightAlias) && colExists(j.rightAlias, j.on.rightCol) === false) {
      errs.push(`join ${i + 1}: column ${j.on.rightCol} not in source ${j.rightAlias}`);
    }
    if (!(j.kind in JOIN_SQL)) {
      errs.push(`join ${i + 1}: unknown join kind ${JSON.stringify(j.kind)}`);
    }
  }

  // ── Filters ────────────────────────────────────────────────────────
  if (graph.filters.length > MAX_FILTERS) {
    errs.push(`too many filters (max ${MAX_FILTERS})`);
  }
  for (let i = 0; i < graph.filters.length; i++) {
    const f = graph.filters[i];
    if (!aliasSet.has(f.alias)) {
      errs.push(`filter ${i + 1}: unknown alias ${f.alias}`);
      continue;
    }
    if (!VALID_IDENTIFIER.test(f.col)) {
      errs.push(`filter ${i + 1}: invalid column name ${JSON.stringify(f.col)}`);
      continue;
    }
    if (!(f.op in OP_SQL)) {
      errs.push(`filter ${i + 1}: unknown operator ${JSON.stringify(f.op)}`);
      continue;
    }
    if (colExists(f.alias, f.col) === false) {
      errs.push(`filter ${i + 1}: column ${f.col} not in source ${f.alias}`);
    }
    if (
      (f.op === "is_null" || f.op === "not_null") &&
      f.value !== undefined &&
      f.value !== ""
    ) {
      // Not a hard error — value is just ignored. Document but accept.
    }
  }

  // ── Group by ───────────────────────────────────────────────────────
  if (graph.groupBy) {
    const seenOutputs = new Set<string>();
    if (graph.groupBy.aggregations.length > MAX_AGGREGATIONS) {
      errs.push(`too many aggregations (max ${MAX_AGGREGATIONS})`);
    }
    for (let i = 0; i < graph.groupBy.cols.length; i++) {
      const c = graph.groupBy.cols[i];
      if (!aliasSet.has(c.alias)) {
        errs.push(`group by ${i + 1}: unknown alias ${c.alias}`);
        continue;
      }
      if (!VALID_IDENTIFIER.test(c.col)) {
        errs.push(`group by ${i + 1}: invalid column name ${JSON.stringify(c.col)}`);
        continue;
      }
      if (colExists(c.alias, c.col) === false) {
        errs.push(`group by ${i + 1}: column ${c.col} not in source ${c.alias}`);
      }
    }
    for (let i = 0; i < graph.groupBy.aggregations.length; i++) {
      const a = graph.groupBy.aggregations[i];
      if (!(a.fn in AGG_FN_SQL)) {
        errs.push(`aggregation ${i + 1}: unknown function ${JSON.stringify(a.fn)}`);
        continue;
      }
      if (!VALID_IDENTIFIER.test(a.outputName)) {
        errs.push(`aggregation ${i + 1}: invalid output name ${JSON.stringify(a.outputName)}`);
        continue;
      }
      const outputKey = a.outputName.toLowerCase();
      if (seenOutputs.has(outputKey)) {
        errs.push(`aggregation ${i + 1}: duplicate output name ${a.outputName}`);
        continue;
      }
      seenOutputs.add(outputKey);
      // count(*) — no alias / col required.
      if (a.fn !== "count") {
        if (!a.alias || !aliasSet.has(a.alias)) {
          errs.push(`aggregation ${i + 1}: ${a.fn.toUpperCase()} requires a source alias`);
          continue;
        }
        if (!a.col || !VALID_IDENTIFIER.test(a.col)) {
          errs.push(`aggregation ${i + 1}: ${a.fn.toUpperCase()} requires a valid column name`);
          continue;
        }
        if (colExists(a.alias, a.col) === false) {
          errs.push(`aggregation ${i + 1}: column ${a.col} not in source ${a.alias}`);
        }
      } else {
        // count(*): allow optional alias+col for COUNT(<alias>.<col>); else COUNT(*)
        if (a.alias && !aliasSet.has(a.alias)) {
          errs.push(`aggregation ${i + 1}: unknown alias ${a.alias}`);
        }
        if (a.col && !VALID_IDENTIFIER.test(a.col)) {
          errs.push(`aggregation ${i + 1}: invalid column name ${JSON.stringify(a.col)}`);
        }
      }
    }
  }

  // ── Order by ───────────────────────────────────────────────────────
  if (graph.orderBy) {
    if (!isValidOrderByCol(graph.orderBy, graph, aliasSet)) {
      errs.push(
        `order by: ${graph.orderBy.col} must be either a group-by output, an aggregation output, or <alias>.<col>`,
      );
    }
    if (graph.orderBy.direction !== "asc" && graph.orderBy.direction !== "desc") {
      errs.push(`order by: direction must be 'asc' or 'desc'`);
    }
  }

  // ── Limit ──────────────────────────────────────────────────────────
  if (graph.limit !== null) {
    if (
      !Number.isInteger(graph.limit) ||
      graph.limit < 1 ||
      graph.limit > MAX_LIMIT
    ) {
      errs.push(`limit must be an integer between 1 and ${MAX_LIMIT}`);
    }
  }

  return errs;
}

function isValidOrderByCol(
  orderBy: OrderByRef,
  graph: FusionGraph,
  aliasSet: Set<string>,
): boolean {
  // Output name from groupBy?
  if (graph.groupBy) {
    const outputs = new Set<string>([
      ...graph.groupBy.cols.map((c) => c.col.toLowerCase()),
      ...graph.groupBy.aggregations.map((a) => a.outputName.toLowerCase()),
    ]);
    if (outputs.has(orderBy.col.toLowerCase())) return true;
  }
  // <alias>.<col> form?
  const dotIdx = orderBy.col.indexOf(".");
  if (dotIdx > 0) {
    const alias = orderBy.col.slice(0, dotIdx);
    const col = orderBy.col.slice(dotIdx + 1);
    if (!aliasSet.has(alias)) return false;
    if (!VALID_IDENTIFIER.test(col)) return false;
    return true;
  }
  // Bare column name (post-groupBy already returned true above);
  // without groupBy it must be a valid identifier referring to a source col,
  // but without alias qualification we can't disambiguate. Reject.
  return false;
}

// ── SQL emission ──────────────────────────────────────────────────────

function emitSelectClause(
  graph: FusionGraph,
): string {
  if (graph.groupBy) {
    const parts: string[] = [];
    for (const c of graph.groupBy.cols) {
      parts.push(`${c.alias}.${quoteIdent(c.col)}`);
    }
    for (const a of graph.groupBy.aggregations) {
      parts.push(emitAggregation(a));
    }
    return parts.length > 0 ? parts.join(", ") : "1";
  }
  // No groupBy — return all columns. Single source: bare *. Multi-source:
  // <alias>.* per source so column names are namespaced.
  if (graph.sources.length === 1) {
    return "*";
  }
  return graph.sources.map((s) => `${s.alias}.*`).join(", ");
}

function emitAggregation(a: GroupByRef["aggregations"][number]): string {
  const out = quoteIdent(a.outputName);
  if (a.fn === "count") {
    if (a.alias && a.col) {
      return `COUNT(${a.alias}.${quoteIdent(a.col)}) AS ${out}`;
    }
    return `COUNT(*) AS ${out}`;
  }
  if (a.fn === "count_distinct") {
    return `COUNT(DISTINCT ${a.alias}.${quoteIdent(a.col!)}) AS ${out}`;
  }
  return `${AGG_FN_SQL[a.fn]}(${a.alias}.${quoteIdent(a.col!)}) AS ${out}`;
}

function emitFromClause(graph: FusionGraph): string {
  const head = graph.sources[0];
  const lines = [`FROM ${qualified(head.pluginId, head.table)} AS ${head.alias}`];
  // Sources after the head must be reachable via a join — but we don't
  // enforce that here; the compiler emits joins in declaration order
  // and the user picks valid (left, right) pairs. If a source is
  // unreferenced, it becomes an implicit cross-join only via joins;
  // sources without any join show up as "FROM s1 a, s2 b" (cartesian)
  // which is what the user asked for. Keep simple.
  for (const j of graph.joins) {
    const right = graph.sources.find((s) => s.alias === j.rightAlias);
    if (!right) continue; // validation already caught this
    lines.push(
      `${JOIN_SQL[j.kind]} ${qualified(right.pluginId, right.table)} AS ${right.alias} ` +
        `ON ${j.leftAlias}.${quoteIdent(j.on.leftCol)} = ${j.rightAlias}.${quoteIdent(j.on.rightCol)}`,
    );
  }
  return lines.join("\n");
}

function emitWhereClause(
  graph: FusionGraph,
  paramSink: unknown[],
): string | null {
  if (graph.filters.length === 0) return null;
  const parts: string[] = [];
  for (const f of graph.filters) {
    parts.push(emitFilter(f, paramSink));
  }
  return `WHERE ${parts.join(" AND ")}`;
}

function emitFilter(
  f: { alias: string; col: string; op: FilterOp; value?: string },
  paramSink: unknown[],
): string {
  const colExpr = `${f.alias}.${quoteIdent(f.col)}`;
  if (f.op === "is_null") return `${colExpr} IS NULL`;
  if (f.op === "not_null") return `${colExpr} IS NOT NULL`;
  if (f.op === "contains") {
    paramSink.push(`%${f.value ?? ""}%`);
    return `${colExpr} ILIKE $${paramSink.length}`;
  }
  if (f.op === "startswith") {
    paramSink.push(`${f.value ?? ""}%`);
    return `${colExpr} ILIKE $${paramSink.length}`;
  }
  paramSink.push(f.value ?? null);
  return `${colExpr} ${OP_SQL[f.op]} $${paramSink.length}`;
}

function emitGroupByClause(graph: FusionGraph): string | null {
  if (!graph.groupBy || graph.groupBy.cols.length === 0) return null;
  const parts = graph.groupBy.cols.map(
    (c) => `${c.alias}.${quoteIdent(c.col)}`,
  );
  return `GROUP BY ${parts.join(", ")}`;
}

function emitOrderByClause(graph: FusionGraph): string | null {
  if (!graph.orderBy) return null;
  const dir = graph.orderBy.direction === "desc" ? "DESC" : "ASC";
  const dotIdx = graph.orderBy.col.indexOf(".");
  let colExpr: string;
  if (dotIdx > 0) {
    const alias = graph.orderBy.col.slice(0, dotIdx);
    const col = graph.orderBy.col.slice(dotIdx + 1);
    colExpr = `${alias}.${quoteIdent(col)}`;
  } else {
    // Output-name reference (groupBy output or aggregation output).
    colExpr = quoteIdent(graph.orderBy.col);
  }
  return `ORDER BY ${colExpr} ${dir}`;
}

function emitLimitClause(graph: FusionGraph): string | null {
  if (graph.limit === null) return null;
  return `LIMIT ${graph.limit}`;
}

// ── Public entry point ───────────────────────────────────────────────

export function compileFusionGraph(
  graph: FusionGraph,
  schemaCache: SchemaCacheLookup = new StaticSchemaCache(),
): CompileResult {
  const errors = validateGraph(graph, schemaCache);
  if (errors.length > 0) {
    return { ok: false, errors };
  }

  const params: unknown[] = [];
  const select = emitSelectClause(graph);
  const from = emitFromClause(graph);
  const where = emitWhereClause(graph, params);
  const groupBy = emitGroupByClause(graph);
  const orderBy = emitOrderByClause(graph);
  const limit = emitLimitClause(graph);

  const lines = [`SELECT ${select}`, from];
  if (where) lines.push(where);
  if (groupBy) lines.push(groupBy);
  if (orderBy) lines.push(orderBy);
  if (limit) lines.push(limit);

  return {
    ok: true,
    sql: lines.join("\n"),
    params,
  };
}
