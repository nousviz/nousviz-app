/**
 * B263 (v0.9.11.7) — unit tests for the visual fusion-graph compiler.
 *
 * The compiler is the single trust boundary between user input (the
 * graph) and executable SQL. Heavy on injection-defense + edge cases.
 *
 * Run via:
 *   cd apps/web && npx tsx src/lib/fusion-compiler.test.ts
 * Assertion failures throw and exit nonzero.
 */

import {
  compileFusionGraph,
  StaticSchemaCache,
  type CompileResult,
} from "./fusion-compiler";
import {
  EMPTY_GRAPH,
  type FusionGraph,
} from "./fusion-graph-types";

let passed = 0;
let failed = 0;
const failures: string[] = [];

function it(name: string, fn: () => void): void {
  try {
    fn();
    passed++;
  } catch (e) {
    failed++;
    const msg = e instanceof Error ? e.message : String(e);
    failures.push(`  ✗ ${name}\n    ${msg}`);
  }
}

function assertEq<T>(actual: T, expected: T, label: string): void {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    throw new Error(
      `${label}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`,
    );
  }
}

function assert(cond: boolean, msg: string): void {
  if (!cond) throw new Error(msg);
}

function ok(r: CompileResult): r is { ok: true; sql: string; params: unknown[] } {
  if (!r.ok) {
    throw new Error(`expected compile success, got errors: ${r.errors.join("; ")}`);
  }
  return true;
}

function failedWith(r: CompileResult, needle: string): void {
  if (r.ok) throw new Error(`expected compile failure containing ${JSON.stringify(needle)}, got ok`);
  if (!r.errors.some((e) => e.includes(needle))) {
    throw new Error(
      `expected an error matching ${JSON.stringify(needle)}, got: ${JSON.stringify(r.errors)}`,
    );
  }
}

// ── Schema cache fixture ────────────────────────────────────────────

const schema = new StaticSchemaCache()
  .set("quickbooks", "invoices", [
    { name: "id" }, { name: "date" }, { name: "amount" }, { name: "status" }, { name: "customer_id" },
  ])
  .set("plausible", "page_views", [
    { name: "date" }, { name: "url" }, { name: "visits" }, { name: "country" },
  ])
  .set("fusions", "weekly_revenue", [
    { name: "week" }, { name: "total" },
  ]);

// ── Empty / minimal graphs ──────────────────────────────────────────

it("rejects empty graph", () => {
  const r = compileFusionGraph(EMPTY_GRAPH, schema);
  failedWith(r, "must have at least one source");
});

it("compiles single source, no clauses", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [{ alias: "s1", pluginId: "quickbooks", table: "invoices" }],
  };
  const r = compileFusionGraph(g, schema);
  ok(r) && (() => {
    assertEq(r.sql, `SELECT *\nFROM "public"."invoices" AS s1`, "single-source SQL");
    assertEq(r.params, [], "no params");
  })();
});

it("multi-source emits aliased star projection", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [
      { alias: "s1", pluginId: "quickbooks", table: "invoices" },
      { alias: "s2", pluginId: "plausible", table: "page_views" },
    ],
  };
  const r = compileFusionGraph(g, schema);
  ok(r) && assert(r.sql.startsWith("SELECT s1.*, s2.*"), "multi-source projection");
});

// ── Filters + parameter binding ─────────────────────────────────────

it("compiles filter eq with $1 param", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [{ alias: "s1", pluginId: "quickbooks", table: "invoices" }],
    filters: [{ alias: "s1", col: "status", op: "eq", value: "paid" }],
  };
  const r = compileFusionGraph(g, schema);
  ok(r) && assertEq(r.sql.includes(`s1."status" = $1`), true, "eq emits placeholder");
  ok(r) && assertEq(r.params, ["paid"], "param value bound");
});

it("compiles each comparison op", () => {
  for (const op of ["eq", "neq", "gt", "lt", "gte", "lte"] as const) {
    const g: FusionGraph = {
      ...EMPTY_GRAPH,
      sources: [{ alias: "s1", pluginId: "quickbooks", table: "invoices" }],
      filters: [{ alias: "s1", col: "amount", op, value: "100" }],
    };
    const r = compileFusionGraph(g, schema);
    ok(r) && assertEq(r.params, ["100"], `${op}: value param`);
  }
});

it("contains wraps value with %x%", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [{ alias: "s1", pluginId: "quickbooks", table: "invoices" }],
    filters: [{ alias: "s1", col: "status", op: "contains", value: "paid" }],
  };
  const r = compileFusionGraph(g, schema);
  ok(r) && assertEq(r.params, ["%paid%"], "contains wraps");
  ok(r) && assert(r.sql.includes("ILIKE $1"), "uses ILIKE");
});

it("startswith appends %", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [{ alias: "s1", pluginId: "quickbooks", table: "invoices" }],
    filters: [{ alias: "s1", col: "status", op: "startswith", value: "p" }],
  };
  const r = compileFusionGraph(g, schema);
  ok(r) && assertEq(r.params, ["p%"], "startswith appends");
});

it("is_null + not_null emit no param", () => {
  for (const op of ["is_null", "not_null"] as const) {
    const g: FusionGraph = {
      ...EMPTY_GRAPH,
      sources: [{ alias: "s1", pluginId: "quickbooks", table: "invoices" }],
      filters: [{ alias: "s1", col: "amount", op }],
    };
    const r = compileFusionGraph(g, schema);
    ok(r) && assertEq(r.params, [], `${op}: no param`);
    ok(r) && assert(r.sql.includes(op === "is_null" ? "IS NULL" : "IS NOT NULL"), `${op}: SQL`);
  }
});

it("multiple filters AND-composed in declaration order", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [{ alias: "s1", pluginId: "quickbooks", table: "invoices" }],
    filters: [
      { alias: "s1", col: "status", op: "eq", value: "paid" },
      { alias: "s1", col: "amount", op: "gt", value: "100" },
      { alias: "s1", col: "date", op: "gte", value: "2026-01-01" },
    ],
  };
  const r = compileFusionGraph(g, schema);
  ok(r) && assert(r.sql.includes("WHERE"), "WHERE present");
  ok(r) && assert(
    r.sql.includes("$1") && r.sql.includes("$2") && r.sql.includes("$3"),
    "three placeholders",
  );
  ok(r) && assertEq(r.params, ["paid", "100", "2026-01-01"], "params in order");
  // AND between filters
  ok(r) && assert(r.sql.match(/AND/g)!.length === 2, "two ANDs joining three filters");
});

// ── Joins ──────────────────────────────────────────────────────────

it("inner join two sources", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [
      { alias: "s1", pluginId: "quickbooks", table: "invoices" },
      { alias: "s2", pluginId: "plausible", table: "page_views" },
    ],
    joins: [
      { kind: "inner", leftAlias: "s1", rightAlias: "s2", on: { leftCol: "date", rightCol: "date" } },
    ],
  };
  const r = compileFusionGraph(g, schema);
  ok(r) && assert(r.sql.includes("INNER JOIN"), "inner join");
  ok(r) && assert(r.sql.includes(`s1."date" = s2."date"`), "ON clause");
});

it("left/right/full join keywords correct", () => {
  for (const [kind, sqlFrag] of [
    ["left", "LEFT JOIN"],
    ["right", "RIGHT JOIN"],
    ["full", "FULL OUTER JOIN"],
  ] as const) {
    const g: FusionGraph = {
      ...EMPTY_GRAPH,
      sources: [
        { alias: "s1", pluginId: "quickbooks", table: "invoices" },
        { alias: "s2", pluginId: "plausible", table: "page_views" },
      ],
      joins: [{ kind, leftAlias: "s1", rightAlias: "s2", on: { leftCol: "date", rightCol: "date" } }],
    };
    const r = compileFusionGraph(g, schema);
    ok(r) && assert(r.sql.includes(sqlFrag), `${kind}: ${sqlFrag}`);
  }
});

it("rejects join with unknown alias", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [{ alias: "s1", pluginId: "quickbooks", table: "invoices" }],
    joins: [{ kind: "inner", leftAlias: "s1", rightAlias: "s99", on: { leftCol: "date", rightCol: "date" } }],
  };
  failedWith(compileFusionGraph(g, schema), "unknown right alias");
});

it("rejects self-join", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [{ alias: "s1", pluginId: "quickbooks", table: "invoices" }],
    joins: [{ kind: "inner", leftAlias: "s1", rightAlias: "s1", on: { leftCol: "date", rightCol: "date" } }],
  };
  failedWith(compileFusionGraph(g, schema), "cannot join an alias to itself");
});

it("rejects join with column not in source schema", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [
      { alias: "s1", pluginId: "quickbooks", table: "invoices" },
      { alias: "s2", pluginId: "plausible", table: "page_views" },
    ],
    joins: [{ kind: "inner", leftAlias: "s1", rightAlias: "s2", on: { leftCol: "nonexistent", rightCol: "date" } }],
  };
  failedWith(compileFusionGraph(g, schema), "column nonexistent not in source s1");
});

// ── Group by + aggregations ────────────────────────────────────────

it("group by with sum aggregation", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [{ alias: "s1", pluginId: "quickbooks", table: "invoices" }],
    groupBy: {
      cols: [{ alias: "s1", col: "date" }],
      aggregations: [{ fn: "sum", alias: "s1", col: "amount", outputName: "total" }],
    },
  };
  const r = compileFusionGraph(g, schema);
  ok(r) && assert(r.sql.includes(`SUM(s1."amount") AS "total"`), "sum aggregation");
  ok(r) && assert(r.sql.includes(`GROUP BY s1."date"`), "group by clause");
});

it("count(*) aggregation needs no alias/col", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [{ alias: "s1", pluginId: "quickbooks", table: "invoices" }],
    groupBy: {
      cols: [],
      aggregations: [{ fn: "count", outputName: "n" }],
    },
  };
  const r = compileFusionGraph(g, schema);
  ok(r) && assert(r.sql.includes(`COUNT(*) AS "n"`), "count(*) emits star");
});

it("count_distinct with column", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [{ alias: "s1", pluginId: "quickbooks", table: "invoices" }],
    groupBy: {
      cols: [],
      aggregations: [{ fn: "count_distinct", alias: "s1", col: "customer_id", outputName: "distinct_customers" }],
    },
  };
  const r = compileFusionGraph(g, schema);
  ok(r) && assert(
    r.sql.includes(`COUNT(DISTINCT s1."customer_id") AS "distinct_customers"`),
    "count distinct emits properly",
  );
});

it("rejects sum without alias/col", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [{ alias: "s1", pluginId: "quickbooks", table: "invoices" }],
    groupBy: { cols: [], aggregations: [{ fn: "sum", outputName: "x" }] },
  };
  failedWith(compileFusionGraph(g, schema), "SUM requires a source alias");
});

it("rejects duplicate aggregation output name", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [{ alias: "s1", pluginId: "quickbooks", table: "invoices" }],
    groupBy: {
      cols: [],
      aggregations: [
        { fn: "sum", alias: "s1", col: "amount", outputName: "t" },
        { fn: "avg", alias: "s1", col: "amount", outputName: "t" },
      ],
    },
  };
  failedWith(compileFusionGraph(g, schema), "duplicate output name");
});

it("rejects aggregation column not in schema", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [{ alias: "s1", pluginId: "quickbooks", table: "invoices" }],
    groupBy: {
      cols: [],
      aggregations: [{ fn: "sum", alias: "s1", col: "nope", outputName: "x" }],
    },
  };
  failedWith(compileFusionGraph(g, schema), "column nope not in source s1");
});

// ── Order by + limit ───────────────────────────────────────────────

it("order by groupBy output name", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [{ alias: "s1", pluginId: "quickbooks", table: "invoices" }],
    groupBy: {
      cols: [{ alias: "s1", col: "date" }],
      aggregations: [{ fn: "sum", alias: "s1", col: "amount", outputName: "total" }],
    },
    orderBy: { col: "total", direction: "desc" },
  };
  const r = compileFusionGraph(g, schema);
  ok(r) && assert(r.sql.includes(`ORDER BY "total" DESC`), "order by output name");
});

it("order by qualified <alias>.<col>", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [{ alias: "s1", pluginId: "quickbooks", table: "invoices" }],
    orderBy: { col: "s1.date", direction: "asc" },
  };
  const r = compileFusionGraph(g, schema);
  ok(r) && assert(r.sql.includes(`ORDER BY s1."date" ASC`), "order by qualified");
});

it("limit clause emitted", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [{ alias: "s1", pluginId: "quickbooks", table: "invoices" }],
    limit: 30,
  };
  const r = compileFusionGraph(g, schema);
  ok(r) && assert(r.sql.includes("LIMIT 30"), "limit emitted");
});

it("rejects limit out of range", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [{ alias: "s1", pluginId: "quickbooks", table: "invoices" }],
    limit: 0,
  };
  failedWith(compileFusionGraph(g, schema), "limit must be an integer");
});

it("rejects limit too high", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [{ alias: "s1", pluginId: "quickbooks", table: "invoices" }],
    limit: 99999,
  };
  failedWith(compileFusionGraph(g, schema), "limit must be an integer");
});

it("rejects orderBy bare col without groupBy", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [{ alias: "s1", pluginId: "quickbooks", table: "invoices" }],
    orderBy: { col: "date", direction: "asc" },
  };
  failedWith(compileFusionGraph(g, schema), "must be either a group-by output");
});

// ── Published fusion sources (B264 integration) ────────────────────

it("published fusion source schema-qualified", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [{ alias: "s1", pluginId: "fusions", table: "weekly_revenue" }],
  };
  const r = compileFusionGraph(g, schema);
  ok(r) && assert(
    r.sql.includes(`FROM "fusions"."weekly_revenue" AS s1`),
    "published fusion qualified with fusions schema",
  );
});

it("published fusion as join source", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [
      { alias: "s1", pluginId: "quickbooks", table: "invoices" },
      { alias: "s2", pluginId: "fusions", table: "weekly_revenue" },
    ],
    joins: [
      { kind: "left", leftAlias: "s1", rightAlias: "s2", on: { leftCol: "date", rightCol: "week" } },
    ],
  };
  const r = compileFusionGraph(g, schema);
  ok(r) && assert(r.sql.includes(`LEFT JOIN "fusions"."weekly_revenue" AS s2`), "join references qualified view");
});

// ── Identifier injection defense ───────────────────────────────────

it("rejects column name with semicolon (injection attempt)", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [{ alias: "s1", pluginId: "quickbooks", table: "invoices" }],
    filters: [{ alias: "s1", col: '"; DROP TABLE x; --', op: "eq", value: "x" }],
  };
  failedWith(compileFusionGraph(g, schema), "invalid column name");
});

it("rejects table name with quotes", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [{ alias: "s1", pluginId: "quickbooks", table: '"; DROP TABLE x; --' }],
  };
  failedWith(compileFusionGraph(g, schema), "invalid table name");
});

it("rejects alias name with non-s-prefix", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [{ alias: 'evil"; --', pluginId: "quickbooks", table: "invoices" }],
  };
  failedWith(compileFusionGraph(g, schema), "invalid source alias");
});

it("rejects unknown filter operator", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [{ alias: "s1", pluginId: "quickbooks", table: "invoices" }],
    // @ts-expect-error intentionally malformed for test
    filters: [{ alias: "s1", col: "amount", op: "BOGUS", value: "1" }],
  };
  failedWith(compileFusionGraph(g, schema), "unknown operator");
});

it("rejects unknown aggregation function", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [{ alias: "s1", pluginId: "quickbooks", table: "invoices" }],
    groupBy: {
      cols: [],
      // @ts-expect-error intentionally malformed for test
      aggregations: [{ fn: "EVIL", alias: "s1", col: "amount", outputName: "x" }],
    },
  };
  failedWith(compileFusionGraph(g, schema), "unknown function");
});

it("value injection through filter value passes through as param (not interpolated)", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [{ alias: "s1", pluginId: "quickbooks", table: "invoices" }],
    filters: [{ alias: "s1", col: "status", op: "eq", value: "' OR 1=1 --" }],
  };
  const r = compileFusionGraph(g, schema);
  ok(r) && assertEq(r.params, ["' OR 1=1 --"], "evil value lands as param");
  ok(r) && assert(!r.sql.includes("OR 1=1"), "evil value NOT interpolated into SQL");
});

it("rejects too many sources", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [
      { alias: "s1", pluginId: "quickbooks", table: "invoices" },
      { alias: "s2", pluginId: "plausible", table: "page_views" },
      { alias: "s3", pluginId: "quickbooks", table: "invoices" },
      { alias: "s4", pluginId: "plausible", table: "page_views" },
      { alias: "s5", pluginId: "quickbooks", table: "invoices" },
    ],
  };
  failedWith(compileFusionGraph(g, schema), "too many sources");
});

it("rejects too many filters", () => {
  const filters = Array.from({ length: 9 }, (_, i) => ({
    alias: "s1",
    col: "status",
    op: "eq" as const,
    value: String(i),
  }));
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [{ alias: "s1", pluginId: "quickbooks", table: "invoices" }],
    filters,
  };
  failedWith(compileFusionGraph(g, schema), "too many filters");
});

// ── End-to-end realistic fusion ─────────────────────────────────────

it("realistic: invoices + page_views joined on date, filtered, grouped, ordered", () => {
  const g: FusionGraph = {
    sources: [
      { alias: "s1", pluginId: "quickbooks", table: "invoices" },
      { alias: "s2", pluginId: "plausible", table: "page_views" },
    ],
    joins: [
      { kind: "left", leftAlias: "s1", rightAlias: "s2", on: { leftCol: "date", rightCol: "date" } },
    ],
    filters: [
      { alias: "s1", col: "status", op: "eq", value: "paid" },
    ],
    groupBy: {
      cols: [{ alias: "s1", col: "date" }],
      aggregations: [
        { fn: "sum", alias: "s1", col: "amount", outputName: "total_revenue" },
        { fn: "count", outputName: "view_count" },
      ],
    },
    orderBy: { col: "total_revenue", direction: "desc" },
    limit: 30,
  };
  const r = compileFusionGraph(g, schema);
  ok(r) && (() => {
    const expected = [
      `SELECT s1."date", SUM(s1."amount") AS "total_revenue", COUNT(*) AS "view_count"`,
      `FROM "public"."invoices" AS s1`,
      `LEFT JOIN "public"."page_views" AS s2 ON s1."date" = s2."date"`,
      `WHERE s1."status" = $1`,
      `GROUP BY s1."date"`,
      `ORDER BY "total_revenue" DESC`,
      `LIMIT 30`,
    ].join("\n");
    assertEq(r.sql, expected, "realistic SQL");
    assertEq(r.params, ["paid"], "single param");
  })();
});

// ── Schema cache behaviour: missing entry → loose mode ──────────────

it("missing schema entry skips column existence check (loose mode)", () => {
  const cache = new StaticSchemaCache(); // empty
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [{ alias: "s1", pluginId: "unknown", table: "weird_table" }],
    filters: [{ alias: "s1", col: "any_col", op: "eq", value: "x" }],
  };
  const r = compileFusionGraph(g, cache);
  // Compiler can't validate the column without a loaded schema — it accepts
  // it in loose mode. Production save paths must pre-warm the cache.
  ok(r) && assert(r.sql.includes(`s1."any_col"`), "loose mode accepts unknown col");
});

// ── B292 (v0.10.0.0) — schema-qualify plugin tables ─────────────────

it("B292: plugin-table source compiles to \"public\".\"<table>\"", () => {
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [{ alias: "s1", pluginId: "quickbooks", table: "invoices" }],
  };
  const r = compileFusionGraph(g, schema);
  ok(r) && assert(
    r.sql.includes(`FROM "public"."invoices" AS s1`),
    `expected qualified FROM, got: ${r.ok ? r.sql : ""}`,
  );
});

it("B292: same-named tables from different plugins both qualified", () => {
  // Real-world collision: two plugins each declaring a `users` table.
  const collisionSchema = new StaticSchemaCache()
    .set("quickbooks", "users", [{ name: "id" }, { name: "email" }])
    .set("plausible", "users", [{ name: "id" }, { name: "url" }]);
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [
      { alias: "s1", pluginId: "quickbooks", table: "users" },
      { alias: "s2", pluginId: "plausible", table: "users" },
    ],
    joins: [
      { kind: "inner", leftAlias: "s1", rightAlias: "s2", on: { leftCol: "id", rightCol: "id" } },
    ],
  };
  const r = compileFusionGraph(g, collisionSchema);
  ok(r) && assert(
    r.sql.includes(`FROM "public"."users" AS s1`),
    `expected qualified FROM for s1, got: ${r.ok ? r.sql : ""}`,
  );
  ok(r) && assert(
    r.sql.includes(`INNER JOIN "public"."users" AS s2`),
    `expected qualified JOIN for s2, got: ${r.ok ? r.sql : ""}`,
  );
});

it("B292: published-fusion source remains \"fusions\".\"<view>\"", () => {
  // Regression pin — qualified() must not double-qualify the fusion path.
  const g: FusionGraph = {
    ...EMPTY_GRAPH,
    sources: [{ alias: "s1", pluginId: "fusions", table: "weekly_revenue" }],
  };
  const r = compileFusionGraph(g, schema);
  ok(r) && assert(
    r.sql.includes(`FROM "fusions"."weekly_revenue" AS s1`),
    `expected fusions-schema FROM, got: ${r.ok ? r.sql : ""}`,
  );
  ok(r) && assert(
    !r.sql.includes(`"public"."weekly_revenue"`),
    `fusion source must not be qualified as public, got: ${r.ok ? r.sql : ""}`,
  );
});

// ── Summary ────────────────────────────────────────────────────────

console.log(`\nfusion-compiler tests: ${passed} passed, ${failed} failed`);
if (failures.length > 0) {
  console.log(failures.join("\n"));
  process.exit(1);
}
