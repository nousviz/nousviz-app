import { useState, useEffect } from "react";
import { AlertTriangle, X, CheckCircle2, Loader2, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { apiFetch } from "@/lib/api";

interface Dependent {
  plugin: string;
  display_name: string;
  reason: string;
}

interface TableInfo {
  table: string;
  engine: string;
}

// B280 (v0.9.11.15): per-table size + row count for the honest uninstall modal
interface TableWithSize {
  name: string;
  size_mb: number;
  rows: number;
}

interface DataDirInfo {
  path: string;
  size_mb: number;
}

interface Reference {
  kind: string;
  id: number;
  display_name: string;
  reason: string;
}

interface UninstallCheck {
  plugin_id: string;
  display_name: string;
  type?: string;
  dependents: Dependent[];
  references?: Reference[];
  tables: TableInfo[];
  data_dirs?: DataDirInfo[];
  has_dependents: boolean;
  has_references?: boolean;
  has_data: boolean;
  // B280 (v0.9.11.15): detailed per-table info for the honest modal
  tables_to_drop_if_data_removed?: TableWithSize[];
  tables_to_drop_total_size_mb?: number;
  tables_to_drop_total_count?: number;
}

interface UninstallResult {
  status: string;
  uninstalled: string[];
  data_removed: boolean;
  restart_required: boolean;
  dependents?: { plugin: string; display_name: string }[];
  // B278 (v0.9.11.14): actual outcome — what was really dropped vs. failed.
  // Empty/missing for older API responses (graceful degradation).
  data_tables_dropped?: string[];
  data_tables_drop_failed?: { table: string; reason: string }[];
  // B281 (v0.9.11.21): per-kind reference cleanup outcomes.
  references_removed?: boolean;
  references_cleanup?: {
    annotations_deleted?: { id: string; title?: string | null }[];
    shares_deleted?: { id: string; label?: string | null }[];
    fusions_repointed?: { id: string; name?: string | null }[];
    alerts_left_alone?: { id: string; name?: string | null }[];
    failed?: { kind: string; id: string; error: string }[];
  };
}

type ModalStep =
  | { name: "checking" }
  | { name: "confirm"; check: UninstallCheck }
  | { name: "uninstalling" }
  | { name: "done"; result: UninstallResult };

interface Props {
  pluginId: string;
  pluginName: string;
  onClose: () => void;
  onComplete: (uninstalledSlugs: string[]) => void;
}

export default function UninstallPluginModal({ pluginId, pluginName, onClose, onComplete }: Props) {
  const [step, setStep] = useState<ModalStep>({ name: "checking" });
  const [removeData, setRemoveData] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [referencesAcked, setReferencesAcked] = useState(false);
  // B281 (v0.9.11.21): opt-in auto-cleanup of orphan references.
  // When ticked, the uninstall request adds ?remove_references=true
  // and the backend deletes annotations + shares + strips fusion
  // requires arrays. Independent from removeData — operator can pick
  // either, both, or neither.
  const [removeReferences, setRemoveReferences] = useState(false);

  useEffect(() => {
    apiFetch(`/api/plugins/${pluginId}/uninstall-check`)
      .then(r => r.json())
      .then((check: UninstallCheck) => setStep({ name: "confirm", check }))
      .catch(() => setStep({ name: "confirm", check: { plugin_id: pluginId, display_name: pluginName, dependents: [], references: [], tables: [], data_dirs: [], has_dependents: false, has_references: false, has_data: false } }));
  }, [pluginId]);

  const handleUninstall = async () => {
    if (step.name !== "confirm") return;
    setStep({ name: "uninstalling" });

    const params = new URLSearchParams();
    if (removeData) params.set("remove_data", "true");
    if (removeReferences) params.set("remove_references", "true");
    if (step.check.has_dependents) params.set("cascade", "true");

    try {
      const r = await apiFetch(`/api/plugins/${pluginId}/install?${params}`, { method: "DELETE" });
      const result: UninstallResult = await r.json();

      if (result.status === "uninstalled") {
        if (result.restart_required) {
          localStorage.setItem("nousviz_restart_required", "true");
          localStorage.setItem("nousviz_restart_set_at", new Date().toISOString());
          // Store display names for the banner message
          const names = (result as any).uninstalled_names || result.uninstalled || [pluginId];
          localStorage.setItem("nousviz_restart_plugin_names", JSON.stringify(names));
        }
        setStep({ name: "done", result });
        onComplete(result.uninstalled || [pluginId]);
      } else {
        // Unexpected status — close and let caller handle
        onClose();
      }
    } catch {
      onClose();
    }
  };

  const pluginCount = step.name === "confirm"
    ? 1 + step.check.dependents.length
    : 1;

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm" onClick={step.name === "done" ? onClose : undefined} />

      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="w-full max-w-md bg-card border border-border rounded-lg shadow-xl">

          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-border">
            <h2 className="font-display text-sm text-foreground">
              {step.name === "checking" && "Checking dependencies…"}
              {step.name === "confirm" && `Uninstall ${step.check.display_name}?`}
              {step.name === "uninstalling" && "Uninstalling…"}
              {step.name === "done" && "Uninstalled"}
            </h2>
            {(step.name === "confirm" || step.name === "done") && (
              <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors">
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Body */}
          <div className="px-5 py-4 space-y-4">

            {/* Checking */}
            {step.name === "checking" && (
              <div className="flex items-center gap-3 text-sm text-muted-foreground py-4">
                <Loader2 className="w-4 h-4 animate-spin shrink-0" />
                Checking for dependent plugins and data impact…
              </div>
            )}

            {/* Confirm */}
            {step.name === "confirm" && (
              <>
                {/* Dependents warning */}
                {step.check.has_dependents && (
                  <div className="rounded-md border border-orange-500/30 bg-orange-500/5 p-3 space-y-2">
                    <div className="flex items-center gap-2 text-sm font-body text-orange-400">
                      <AlertTriangle className="w-4 h-4 shrink-0" />
                      Dependent plugins will also be uninstalled
                    </div>
                    <ul className="space-y-1 pl-6">
                      {step.check.dependents.map(dep => (
                        <li key={dep.plugin} className="text-xs text-muted-foreground">
                          <span className="text-foreground">{dep.display_name}</span>
                          {dep.reason && <span className="ml-1">— {dep.reason}</span>}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* References that will break — operator picks: auto-clean or
                    manually acknowledge. Independent from data-tables checkbox. */}
                {step.check.has_references && step.check.references && step.check.references.length > 0 && (
                  <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 space-y-2">
                    <div className="flex items-center gap-2 text-sm font-body text-destructive">
                      <AlertTriangle className="w-4 h-4 shrink-0" />
                      References that will break
                    </div>
                    <p className="text-xs text-muted-foreground">
                      These reference the plugin. Auto-clean to remove them with the uninstall, or acknowledge that you'll clean them up manually.
                    </p>
                    <ul className="space-y-1 pl-6 max-h-40 overflow-y-auto">
                      {step.check.references.map(ref => (
                        <li key={`${ref.kind}-${ref.id}`} className="text-xs text-muted-foreground">
                          <span className="text-[10px] uppercase tracking-wider font-display text-destructive/80 mr-1.5">{ref.kind}</span>
                          <span className="text-foreground">{ref.display_name}</span>
                          {ref.reason && <span className="ml-1">— {ref.reason}</span>}
                        </li>
                      ))}
                    </ul>
                    {/* B281 (v0.9.11.21): auto-clean checkbox — opt-in.
                        Ticking this satisfies the references gate (no
                        manual ack required because the backend will
                        clean them up). */}
                    <label className="flex items-start gap-2 pt-2 text-xs text-foreground cursor-pointer rounded border border-border bg-card/50 p-2">
                      <input
                        type="checkbox"
                        checked={removeReferences}
                        onChange={e => {
                          setRemoveReferences(e.target.checked);
                          if (e.target.checked) setReferencesAcked(false);
                        }}
                        className="accent-primary mt-0.5"
                      />
                      <span>
                        <span className="text-foreground">Auto-clean these {step.check.references.length} reference{step.check.references.length !== 1 ? "s" : ""}</span>
                        <span className="block text-[11px] text-muted-foreground mt-0.5">
                          Annotations and shared links get deleted. Fusions get the plugin stripped from their <code className="font-mono-deck">requires</code> array but the fusion itself is preserved (so you can repoint widgets later). Alert rules are left alone — handle them via the alerts page.
                        </span>
                      </span>
                    </label>
                    {/* Manual-cleanup acknowledgement — only required when
                        the operator did NOT tick auto-clean above. */}
                    {!removeReferences && (
                      <label className="flex items-center gap-2 pt-1 text-xs text-foreground cursor-pointer">
                        <input
                          type="checkbox"
                          checked={referencesAcked}
                          onChange={e => setReferencesAcked(e.target.checked)}
                          className="accent-destructive"
                        />
                        <span>
                          Or — I'll clean up these {step.check.references.length} reference{step.check.references.length !== 1 ? "s" : ""} manually after uninstall.
                        </span>
                      </label>
                    )}
                  </div>
                )}

                {/* Data removal */}
                {step.check.has_data && (() => {
                  const hasTables = step.check.tables.length > 0;
                  const hasDirs = (step.check.data_dirs?.length ?? 0) > 0;
                  // Pick label based on what exists: utility plugins have dirs, regular plugins have tables
                  const noun = hasTables && hasDirs ? "tables and data"
                    : hasDirs ? "data"
                    : "tables";
                  const keepPhrase = hasDirs && !hasTables ? "keep data" : "keep tables";
                  const deletePhrase = hasDirs && !hasTables ? "delete data" : "delete tables";
                  return (
                  <div className="space-y-2">
                    {hasTables && (
                      <>
                        <p className="text-xs font-body text-muted-foreground">
                          Plugin data tables
                          {/* B280: total size summary when sizes are available */}
                          {(step.check.tables_to_drop_total_count ?? 0) > 0 && (
                            <span className="ml-1 text-foreground">
                              · {step.check.tables_to_drop_total_size_mb} MB across {step.check.tables_to_drop_total_count} table{(step.check.tables_to_drop_total_count ?? 0) !== 1 ? "s" : ""}
                            </span>
                          )}
                        </p>
                        <div className="rounded-md border border-border bg-background p-2 space-y-1 max-h-40 overflow-y-auto">
                          {step.check.tables.map(t => {
                            // B280: enrich with size/rows if available
                            const detail = step.check.tables_to_drop_if_data_removed?.find(
                              d => d.name === t.table
                            );
                            return (
                              <div key={`${t.engine}-${t.table}`} className="flex items-center justify-between gap-2 text-xs">
                                <span className="font-mono-deck text-foreground truncate">{t.table}</span>
                                <span className="text-muted-foreground shrink-0 flex items-center gap-2">
                                  {detail ? (
                                    <>
                                      <span>{detail.size_mb} MB</span>
                                      <span className="opacity-70">{detail.rows.toLocaleString()} row{detail.rows !== 1 ? "s" : ""}</span>
                                    </>
                                  ) : (
                                    <span className="opacity-70">{t.engine}</span>
                                  )}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      </>
                    )}
                    {hasDirs && (
                      <>
                        <p className="text-xs font-body text-muted-foreground">
                          {hasTables ? "Data directories" : "Plugin data"}
                        </p>
                        <div className="rounded-md border border-border bg-background p-2 space-y-1 max-h-32 overflow-y-auto">
                          {step.check.data_dirs!.map(d => (
                            <div key={d.path} className="flex items-center justify-between text-xs">
                              <span className="font-mono-deck text-foreground truncate">{d.path}</span>
                              <span className="text-muted-foreground shrink-0 ml-2">{d.size_mb} MB</span>
                            </div>
                          ))}
                        </div>
                      </>
                    )}
                    <div className="flex items-center gap-3 pt-1">
                      <button
                        onClick={() => { setRemoveData(false); setConfirmText(""); }}
                        className={cn(
                          "flex items-center gap-2 text-xs px-3 py-1.5 rounded-md border transition-colors",
                          !removeData
                            ? "border-primary bg-primary/10 text-primary"
                            : "border-border text-muted-foreground hover:text-foreground"
                        )}
                      >
                        Keep {noun}
                      </button>
                      <button
                        onClick={() => { setRemoveData(true); setConfirmText(""); }}
                        className={cn(
                          "flex items-center gap-2 text-xs px-3 py-1.5 rounded-md border transition-colors",
                          removeData
                            ? "border-destructive bg-destructive/10 text-destructive"
                            : "border-border text-muted-foreground hover:text-foreground"
                        )}
                      >
                        Remove {noun}
                      </button>
                    </div>
                    {!removeData && (
                      <p className="text-xs text-muted-foreground">
                        {hasTables
                          ? <>Tables remain in Postgres but will be inaccessible without the plugin.{" "}
                              <a
                                href="/analytics"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-primary underline hover:text-primary/80"
                              >
                                Export first
                              </a>{" "}
                              if you need the data.
                            </>
                          : "Data files remain on disk. Reinstalling the plugin later will pick them up."}
                      </p>
                    )}
                    {removeData && (
                      <p className="text-xs text-destructive/80">
                        {noun.charAt(0).toUpperCase() + noun.slice(1)} will be permanently deleted. This cannot be undone.
                      </p>
                    )}
                    <input
                      autoFocus
                      type="text"
                      value={confirmText}
                      onChange={e => setConfirmText(e.target.value)}
                      placeholder={`Type "${removeData ? deletePhrase : keepPhrase}" to confirm`}
                      className="w-full rounded-md border border-border bg-background px-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                  </div>
                  );
                })()}

                {/* No dependents, no references, no data — simple confirmation */}
                {!step.check.has_dependents && !step.check.has_references && !step.check.has_data && (
                  <p className="text-sm text-muted-foreground">
                    This will remove the plugin files. Plugin routes will remain active until the API restarts.
                  </p>
                )}
              </>
            )}

            {/* Uninstalling */}
            {step.name === "uninstalling" && (
              <div className="flex items-center gap-3 text-sm text-muted-foreground py-4">
                <Loader2 className="w-4 h-4 animate-spin shrink-0" />
                Removing plugin{pluginCount > 1 ? `s (${pluginCount})` : ""}…
              </div>
            )}

            {/* Done */}
            {step.name === "done" && (
              <div className="space-y-3">
                {step.result.uninstalled.map(slug => (
                  <div key={slug} className="flex items-center gap-2 text-sm text-foreground">
                    <CheckCircle2 className="w-4 h-4 text-green-400 shrink-0" />
                    {slug} uninstalled
                  </div>
                ))}

                {/* B278 (v0.9.11.14) + B280 (v0.9.11.15): honest outcome.
                    Show what was actually dropped (and what failed) instead of
                    just echoing the operator's intent flag. */}
                {step.result.data_tables_dropped && step.result.data_tables_dropped.length > 0 && (
                  <div className="rounded-md border border-green-500/30 bg-green-500/5 p-3 space-y-2">
                    <div className="flex items-center gap-2 text-sm text-green-400">
                      <CheckCircle2 className="w-4 h-4 shrink-0" />
                      Tables dropped ({step.result.data_tables_dropped.length})
                    </div>
                    <ul className="pl-6 space-y-1">
                      {step.result.data_tables_dropped.map(name => (
                        <li key={name} className="text-xs font-mono-deck text-muted-foreground">{name}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {step.result.data_removed && (!step.result.data_tables_dropped || step.result.data_tables_dropped.length === 0) && (
                  <div className="flex items-center gap-2 text-sm text-foreground">
                    <CheckCircle2 className="w-4 h-4 text-green-400 shrink-0" />
                    Plugin data removed
                  </div>
                )}

                {/* B278: per-table failure surface — operator gets the SQL
                    they need to manually clean up anything we couldn't drop. */}
                {step.result.data_tables_drop_failed && step.result.data_tables_drop_failed.length > 0 && (
                  <div className="rounded-md border border-orange-500/30 bg-orange-500/5 p-3 space-y-2">
                    <div className="flex items-center gap-2 text-sm text-orange-400">
                      <AlertTriangle className="w-4 h-4 shrink-0" />
                      Some tables didn't drop ({step.result.data_tables_drop_failed.length})
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Manual cleanup required. Run on the server:
                    </p>
                    <pre className="rounded bg-background border border-border p-2 text-[10px] font-mono-deck text-foreground overflow-x-auto">
{step.result.data_tables_drop_failed.map(f =>
  `DROP TABLE IF EXISTS ${f.table} CASCADE;`
).join("\n")}
                    </pre>
                    <details className="text-xs">
                      <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                        Show failure reasons
                      </summary>
                      <ul className="pl-6 space-y-1 mt-2">
                        {step.result.data_tables_drop_failed.map(f => (
                          <li key={f.table} className="text-xs text-muted-foreground">
                            <span className="font-mono-deck text-foreground">{f.table}</span>
                            <span className="ml-1">— {f.reason}</span>
                          </li>
                        ))}
                      </ul>
                    </details>
                  </div>
                )}

                {/* B281 (v0.9.11.21): references cleanup post-summary. */}
                {step.result.references_removed && step.result.references_cleanup && (() => {
                  const c = step.result.references_cleanup!;
                  const totalCleaned =
                    (c.annotations_deleted?.length ?? 0) +
                    (c.shares_deleted?.length ?? 0) +
                    (c.fusions_repointed?.length ?? 0);
                  const failedCount = c.failed?.length ?? 0;
                  return (
                    <>
                      {totalCleaned > 0 && (
                        <div className="rounded-md border border-green-500/30 bg-green-500/5 p-3 space-y-1">
                          <div className="flex items-center gap-2 text-sm text-green-400">
                            <CheckCircle2 className="w-4 h-4 shrink-0" />
                            References cleaned up
                          </div>
                          <ul className="pl-6 space-y-0.5 text-xs text-muted-foreground">
                            {(c.annotations_deleted?.length ?? 0) > 0 && (
                              <li>
                                <span className="text-foreground">{c.annotations_deleted!.length}</span> annotation{c.annotations_deleted!.length !== 1 ? "s" : ""} deleted
                              </li>
                            )}
                            {(c.shares_deleted?.length ?? 0) > 0 && (
                              <li>
                                <span className="text-foreground">{c.shares_deleted!.length}</span> shared link{c.shares_deleted!.length !== 1 ? "s" : ""} deleted
                              </li>
                            )}
                            {(c.fusions_repointed?.length ?? 0) > 0 && (
                              <li>
                                <span className="text-foreground">{c.fusions_repointed!.length}</span> fusion{c.fusions_repointed!.length !== 1 ? "s" : ""} repointed (plugin removed from <code className="font-mono-deck">requires</code>)
                              </li>
                            )}
                            {(c.alerts_left_alone?.length ?? 0) > 0 && (
                              <li className="text-muted-foreground/80">
                                {c.alerts_left_alone!.length} alert rule{c.alerts_left_alone!.length !== 1 ? "s" : ""} left in place — handle them via the alerts page
                              </li>
                            )}
                          </ul>
                        </div>
                      )}
                      {failedCount > 0 && (
                        <div className="rounded-md border border-orange-500/30 bg-orange-500/5 p-3 space-y-2">
                          <div className="flex items-center gap-2 text-sm text-orange-400">
                            <AlertTriangle className="w-4 h-4 shrink-0" />
                            {failedCount} reference cleanup{failedCount !== 1 ? "s" : ""} failed
                          </div>
                          <p className="text-xs text-muted-foreground">
                            Manual cleanup needed. Failure detail:
                          </p>
                          <ul className="pl-6 space-y-1">
                            {c.failed!.map((f, i) => (
                              <li key={`${f.kind}-${f.id}-${i}`} className="text-xs text-muted-foreground">
                                <span className="text-[10px] uppercase tracking-wider font-display text-orange-400/80 mr-1.5">{f.kind}</span>
                                <span className="text-foreground">{f.id}</span>
                                <span className="ml-1">— {f.error}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </>
                  );
                })()}

                {step.result.restart_required && (
                  <div className="rounded-md border border-orange-500/30 bg-orange-500/5 p-3">
                    <div className="flex items-center gap-2 text-sm text-orange-400">
                      <RefreshCw className="w-4 h-4 shrink-0" />
                      API restart required
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Plugin routes remain active until the API server restarts.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Footer */}
          {(step.name === "confirm" || step.name === "done") && (
            <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-border">
              {step.name === "confirm" && (
                <>
                  <button
                    onClick={onClose}
                    className="px-4 py-2 rounded-md text-sm font-body text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleUninstall}
                    disabled={(() => {
                      if (step.name !== "confirm") return false;
                      // B281 (v0.9.11.21): the references gate is satisfied
                      // by EITHER opting into auto-clean OR explicitly
                      // acknowledging manual cleanup.
                      if (step.check.has_references && !removeReferences && !referencesAcked) return true;
                      // Gate on type-to-confirm if data exists
                      if (step.check.has_data) {
                        const hasDirs = (step.check.data_dirs?.length ?? 0) > 0;
                        const hasTables = step.check.tables.length > 0;
                        const keepPhrase = hasDirs && !hasTables ? "keep data" : "keep tables";
                        const deletePhrase = hasDirs && !hasTables ? "delete data" : "delete tables";
                        return confirmText.trim().toLowerCase() !== (removeData ? deletePhrase : keepPhrase);
                      }
                      return false;
                    })()}
                    className="px-4 py-2 rounded-md text-sm font-body bg-destructive text-destructive-foreground hover:bg-destructive/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    Uninstall {pluginCount > 1 ? `${pluginCount} plugins` : pluginName}
                  </button>
                </>
              )}
              {step.name === "done" && (
                <button
                  onClick={onClose}
                  className="px-4 py-2 rounded-md text-sm font-body bg-secondary text-foreground hover:bg-secondary/80 transition-colors"
                >
                  Close
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
