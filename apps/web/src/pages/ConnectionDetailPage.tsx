import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Database,
  ExternalLink,
  RefreshCw,
  Search,
  Server,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import { cn, formatNumber } from "@/lib/utils";
import { useMarkBootReadyOnMount } from "@/components/layout/BootCoordinator";

interface TableEntry {
  name: string;
  table_type: string;
  row_count_estimate: number | null;
}

interface SchemaGroup {
  name: string;
  tables: TableEntry[];
}

interface ConnectionTablesResponse {
  connection: {
    id: string;
    name: string;
    type: string;
    database: string;
  };
  schemas: SchemaGroup[];
}

export default function ConnectionDetailPage() {
  useMarkBootReadyOnMount();
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<ConnectionTablesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<{ status: number; detail: string } | null>(null);
  const [search, setSearch] = useState("");

  async function load() {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch(`/api/connections/${encodeURIComponent(id)}/tables`);
      if (!res.ok) {
        let detail = await res.text();
        try {
          const parsed = JSON.parse(detail);
          if (parsed?.detail) detail = String(parsed.detail);
        } catch {
          /* keep raw text */
        }
        setError({ status: res.status, detail });
        setData(null);
        return;
      }
      setData(await res.json());
    } catch (e) {
      setError({
        status: 0,
        detail: e instanceof Error ? e.message : "Failed to load tables",
      });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const totalTables =
    data?.schemas.reduce((acc, s) => acc + s.tables.length, 0) ?? 0;

  const filteredSchemas =
    data?.schemas
      .map((s) => ({
        ...s,
        tables: s.tables.filter((t) =>
          t.name.toLowerCase().includes(search.toLowerCase()),
        ),
      }))
      .filter((s) => s.tables.length > 0) ?? [];

  return (
    <div className="max-w-[1200px] space-y-5">
      <Link
        to="/connections"
        className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="w-3 h-3" /> Back to Connections
      </Link>

      {/* Header */}
      <div className="bg-card rounded-lg border border-border p-5">
        <div className="flex items-center gap-4">
          <div className="h-10 w-10 rounded-lg bg-blue-500/10 flex items-center justify-center shrink-0">
            <Server className="w-5 h-5 text-blue-400" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-display text-sm text-foreground truncate">
                {data?.connection.name ?? id}
              </span>
              {data && (
                <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-secondary text-muted-foreground uppercase tracking-wider">
                  {data.connection.type}
                </span>
              )}
            </div>
            <p className="text-xs text-muted-foreground mt-0.5 font-mono-deck truncate">
              {data?.connection.database || (loading ? "Loading…" : "")}
              {data && totalTables > 0 && (
                <span className="ml-1.5 opacity-60">
                  · {totalTables} table{totalTables !== 1 ? "s" : ""}
                </span>
              )}
            </p>
          </div>
          <button
            onClick={load}
            disabled={loading}
            className="h-8 w-8 rounded-md bg-secondary hover:bg-secondary/80 flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
            title="Refresh"
          >
            <RefreshCw className={cn("w-3.5 h-3.5", loading && "animate-spin")} />
          </button>
        </div>
      </div>

      {/* Error states */}
      {error && error.status === 501 && (
        <div className="rounded-lg border border-yellow-500/20 bg-yellow-500/5 px-4 py-3 text-sm text-yellow-300">
          {error.detail}
        </div>
      )}
      {error && error.status === 502 && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-400 space-y-2">
          <p className="font-medium">Could not reach the database.</p>
          <p className="text-xs opacity-80">{error.detail}</p>
          <p className="text-xs">
            Verify the connection on the{" "}
            <Link to="/connections" className="underline hover:text-foreground">
              Connections page
            </Link>{" "}
            (test, check credentials).
          </p>
        </div>
      )}
      {error && error.status !== 501 && error.status !== 502 && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-400">
          {error.detail}
        </div>
      )}

      {/* Search + tables list */}
      {!error && (
        <>
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <p className="text-sm text-muted-foreground font-body">
              Tables in this connection's database.
            </p>
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
              <input
                type="text"
                placeholder="Filter tables…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="h-8 pl-8 pr-3 w-56 rounded-md bg-secondary border border-border text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
          </div>

          {loading && !data && (
            <div className="space-y-2">
              {[...Array(6)].map((_, i) => (
                <div
                  key={i}
                  className="h-10 bg-secondary/40 rounded-md animate-pulse"
                />
              ))}
            </div>
          )}

          {!loading && data && totalTables === 0 && (
            <div className="py-16 text-center border border-dashed border-border rounded-lg">
              <Database className="w-8 h-8 text-muted-foreground/40 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground">
                No tables found in this database.
              </p>
            </div>
          )}

          {!loading && data && totalTables > 0 && filteredSchemas.length === 0 && (
            <p className="text-center text-sm text-muted-foreground py-8">
              No tables match your filter.
            </p>
          )}

          {!loading &&
            data &&
            filteredSchemas.map((schemaGroup) => (
              <div key={schemaGroup.name} className="space-y-2">
                <div className="flex items-center gap-2">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">
                    Schema: {schemaGroup.name}
                  </p>
                  <span className="text-[10px] text-muted-foreground">
                    {schemaGroup.tables.length} table
                    {schemaGroup.tables.length !== 1 ? "s" : ""}
                  </span>
                </div>
                <div className="space-y-1.5">
                  {schemaGroup.tables.map((t) => (
                    <Link
                      key={`${schemaGroup.name}.${t.name}`}
                      to={`/connections/${encodeURIComponent(id!)}/tables/${encodeURIComponent(schemaGroup.name)}/${encodeURIComponent(t.name)}`}
                      className="flex items-center gap-3 px-4 py-2.5 rounded-md bg-card border border-border text-xs hover:border-primary/40 transition-colors group"
                    >
                      <Database className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-mono-deck text-foreground group-hover:text-primary transition-colors">
                            {t.name}
                          </span>
                          {t.table_type !== "BASE TABLE" && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-secondary text-muted-foreground">
                              {t.table_type.toLowerCase()}
                            </span>
                          )}
                        </div>
                      </div>
                      <span className="font-mono-deck text-muted-foreground shrink-0">
                        {t.row_count_estimate != null
                          ? `~${formatNumber(t.row_count_estimate)} rows`
                          : "—"}
                      </span>
                      <ExternalLink className="w-3 h-3 text-muted-foreground shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </Link>
                  ))}
                </div>
              </div>
            ))}
        </>
      )}
    </div>
  );
}
