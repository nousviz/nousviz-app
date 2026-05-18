/**
 * AccessTab — per-resource ACL admin (B248, v0.9.10.7).
 *
 * Mounted on dashboard / fusion / share / connection / plugin detail
 * pages. Operators with rbac.edit list, grant, and revoke per-resource
 * grants. Backed by /api/resource-acls/* (see apps/api/src/routes/resource_acls.py).
 *
 * Visibility model: this component shows when the viewer holds rbac.edit.
 * Non-admin viewers see nothing — the resource owner already has implicit
 * access via the resolver, so they don't need to see the ACL surface.
 */

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Trash2, Plus, Shield, AlertTriangle } from "lucide-react";

interface AclGrant {
  id: number;
  resource_type: string;
  resource_id: string;
  principal_kind: string;
  principal_id: string;
  permission: string;
  granted_by?: string | null;
  note?: string | null;
  created_at?: string | null;
}

interface AclList {
  resource_type: string;
  resource_id: string;
  default_policy: string;
  grants: AclGrant[];
}

interface Props {
  resourceType: "dashboard" | "fusion" | "connection" | "share" | "plugin";
  resourceId: string;
  /** Permission strings the user can grant on this resource type. */
  permissions: string[];
}

export function AccessTab({ resourceType, resourceId, permissions }: Props) {
  const [data, setData] = useState<AclList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch(
        `/api/resource-acls/${resourceType}/${encodeURIComponent(resourceId)}`,
      );
      if (res.status === 403) {
        setData(null);
        setError("forbidden");
        return;
      }
      if (!res.ok) {
        throw new Error(`${res.status} ${res.statusText}`);
      }
      const body = (await res.json()) as AclList;
      setData(body);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [resourceType, resourceId]);

  useEffect(() => {
    void load();
  }, [load]);

  const onRevoke = async (grantId: number) => {
    if (!confirm("Revoke this grant?")) return;
    const res = await apiFetch(
      `/api/resource-acls/${resourceType}/${encodeURIComponent(resourceId)}/${grantId}`,
      { method: "DELETE" },
    );
    if (!res.ok) {
      alert(`Revoke failed: ${res.status} ${res.statusText}`);
      return;
    }
    await load();
  };

  if (error === "forbidden") {
    // Caller lacks rbac.edit — render nothing; the resource still works.
    return null;
  }

  return (
    <section className="border border-border rounded-md p-4 space-y-3">
      <header className="flex items-center justify-between">
        <h3 className="text-sm font-semibold flex items-center gap-2">
          <Shield className="w-4 h-4" />
          Access
        </h3>
        {data && (
          <span className="text-xs text-muted-foreground">
            Default policy: <span className="font-mono">{data.default_policy}</span>
          </span>
        )}
      </header>

      {loading && <p className="text-xs text-muted-foreground">Loading…</p>}

      {error && error !== "forbidden" && (
        <p className="text-xs text-red-600 flex items-center gap-1">
          <AlertTriangle className="w-3 h-3" /> {error}
        </p>
      )}

      {data && data.grants.length === 0 && !adding && (
        <p className="text-xs text-muted-foreground">
          No explicit grants. Access is governed by role permissions and the
          default policy.
        </p>
      )}

      {data && data.grants.length > 0 && (
        <table className="w-full text-xs">
          <thead className="text-muted-foreground">
            <tr>
              <th className="text-left font-normal pb-1">Principal</th>
              <th className="text-left font-normal pb-1">Permission</th>
              <th className="text-left font-normal pb-1">Note</th>
              <th className="w-8"></th>
            </tr>
          </thead>
          <tbody>
            {data.grants.map(g => (
              <tr key={g.id} className="border-t border-border/40">
                <td className="py-1.5">
                  <span className="text-muted-foreground">{g.principal_kind}:</span>{" "}
                  <span className="font-mono">{g.principal_id}</span>
                </td>
                <td className="py-1.5 font-mono">{g.permission}</td>
                <td className="py-1.5 text-muted-foreground">{g.note || ""}</td>
                <td className="py-1.5 text-right">
                  <button
                    type="button"
                    onClick={() => void onRevoke(g.id)}
                    title="Revoke grant"
                    className="text-muted-foreground hover:text-red-600"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {adding ? (
        <NewGrantForm
          resourceType={resourceType}
          resourceId={resourceId}
          permissions={permissions}
          onCancel={() => setAdding(false)}
          onSaved={async () => {
            setAdding(false);
            await load();
          }}
        />
      ) : (
        data && (
          <button
            type="button"
            onClick={() => setAdding(true)}
            className="text-xs flex items-center gap-1 text-blue-600 hover:underline"
          >
            <Plus className="w-3 h-3" /> Add grant
          </button>
        )
      )}
    </section>
  );
}

function NewGrantForm(props: {
  resourceType: string;
  resourceId: string;
  permissions: string[];
  onCancel: () => void;
  onSaved: () => Promise<void> | void;
}) {
  const { resourceType, resourceId, permissions, onCancel, onSaved } = props;
  const [principalKind, setPrincipalKind] = useState<"role" | "user">("role");
  const [principalId, setPrincipalId] = useState("");
  const [permission, setPermission] = useState(permissions[0] ?? "");
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!principalId.trim() || !permission) {
      setErr("Principal and permission are required.");
      return;
    }
    setSubmitting(true);
    setErr(null);
    try {
      const res = await apiFetch(
        `/api/resource-acls/${resourceType}/${encodeURIComponent(resourceId)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            principal_kind: principalKind,
            principal_id: principalId.trim(),
            permission,
            note: note.trim() || null,
          }),
        },
      );
      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as { detail?: string };
        throw new Error(body.detail || `${res.status} ${res.statusText}`);
      }
      await onSaved();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={submit} className="border-t border-border/40 pt-3 space-y-2">
      <div className="grid grid-cols-2 gap-2">
        <label className="text-xs flex flex-col gap-1">
          Principal kind
          <select
            value={principalKind}
            onChange={e => setPrincipalKind(e.target.value as "role" | "user")}
            className="border border-border rounded px-2 py-1 bg-background"
          >
            <option value="role">role</option>
            <option value="user">user</option>
          </select>
        </label>
        <label className="text-xs flex flex-col gap-1">
          {principalKind === "role" ? "Role name" : "User id"}
          <input
            value={principalId}
            onChange={e => setPrincipalId(e.target.value)}
            placeholder={principalKind === "role" ? "analyst" : "user uuid"}
            className="border border-border rounded px-2 py-1 bg-background font-mono"
          />
        </label>
        <label className="text-xs flex flex-col gap-1">
          Permission
          <select
            value={permission}
            onChange={e => setPermission(e.target.value)}
            className="border border-border rounded px-2 py-1 bg-background font-mono"
          >
            {permissions.map(p => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs flex flex-col gap-1">
          Note (optional)
          <input
            value={note}
            onChange={e => setNote(e.target.value)}
            placeholder="why this grant exists"
            className="border border-border rounded px-2 py-1 bg-background"
          />
        </label>
      </div>
      {err && (
        <p className="text-xs text-red-600 flex items-center gap-1">
          <AlertTriangle className="w-3 h-3" /> {err}
        </p>
      )}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={submitting}
          className="text-xs px-3 py-1 rounded bg-blue-600 text-white disabled:opacity-50"
        >
          {submitting ? "Saving…" : "Grant"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="text-xs px-3 py-1 rounded border border-border"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
