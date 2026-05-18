/**
 * useCurrentUser — shared hook + context for the authenticated user.
 *
 * B230 (v0.9.8.3): introduced so role-aware UI (sidebar nav, gated pages,
 * conditional buttons) can read the current user from a single source
 * instead of every component re-fetching /api/auth/me.
 *
 * Permission set is fetched from /api/auth/me/permissions — backend is the
 * single source of truth.
 *
 * B236 (v0.9.10.0): rewritten for Option B identity model. The previous
 * v0.9.8.4 "preview as" mode (frontend-only, sessionStorage-backed) is
 * deleted entirely. Real impersonation replaces it. Identity shape now
 * comes from the backend in two layers:
 *
 *   user                              — the actor (always the real human)
 *   user.acting_as                    — the target if impersonating, else undefined
 *
 * `useEffectiveIdentity()` returns the effective user (target if
 * impersonating, actor otherwise) — the canonical place for UI code that
 * gates on identity / displays a name / shows a role badge.
 *
 * `useImpersonating()` returns true iff the session is impersonating.
 *
 * Audit / actor-aware code (the impersonation banner, the "Exit"
 * button, log-out) reads `useCurrentUser().user` to get the actor.
 */

import {
  createContext, useContext, useEffect, useMemo, useRef, useState,
  type ReactNode,
} from "react";
import { apiFetch } from "@/lib/api";

export type Role = "viewer" | "analyst" | "admin" | "superadmin" | string;

const BUILTIN_ROLE_RANK: Record<string, number> = {
  viewer: 1,
  analyst: 2,
  admin: 3,
  superadmin: 4,
};

/**
 * Effective identity: the user the session is currently *acting as* for
 * permission and UI display purposes. Target during impersonation,
 * actor otherwise.
 *
 * Use this for sidebar nav gates, role badges, "what can this user
 * see?" questions, avatars, name displays. NOT for audit logging or
 * the "Exit impersonation" banner — those need the actor (use the
 * `user` field on `useCurrentUser()` instead).
 */
export interface EffectiveIdentity {
  id: string;
  email: string;
  name: string | null;
  role: Role;
  avatar_url: string | null;
}

/**
 * Side-field describing the impersonation target. Present on `user`
 * iff the session is currently impersonating someone.
 */
export interface ActingAs {
  id: string;
  email: string;
  name: string | null;
  role: Role;
  avatar_url: string | null;
}

/**
 * The actor — the real human authenticated to this session. Always
 * present (never null when authenticated). When impersonating, the
 * `acting_as` side field carries the target.
 */
export interface CurrentUser {
  id: string;
  email: string;
  name: string | null;
  role: Role;
  avatar_url: string | null;
  acting_as?: ActingAs;
}

interface CurrentUserContextValue {
  /** The actor — the real human authenticated to this session. */
  user: CurrentUser | null;
  /** The effective user (target if impersonating, else actor). */
  effective: EffectiveIdentity | null;
  /** Permission set for the EFFECTIVE user. Resolved server-side. */
  permissions: ReadonlySet<string>;
  /** True iff the session is impersonating another user. */
  impersonating: boolean;
  /**
   * B254 (v0.9.10.0.5): set when an impersonation just auto-expired
   * (acting_as flipped from set to unset between two refreshes). The
   * value is the just-impersonated target's display label so the
   * toast can say "Returned from impersonating Alice." Cleared by
   * `dismissExpiredImpersonation()` and on the next refresh.
   */
  recentlyExpiredImpersonationLabel: string | null;
  dismissExpiredImpersonation: () => void;
  loading: boolean;
  error: string | null;
  refresh: () => void;
  /** Compares the EFFECTIVE role's rank against the target's rank. */
  hasRole: (target: Role) => boolean;
  hasAnyRole: (...targets: Role[]) => boolean;
  /** Permission predicate against the effective permission set. */
  hasPermission: (permission: string) => boolean;
}

const EMPTY_PERMS: ReadonlySet<string> = new Set();

const CurrentUserContext = createContext<CurrentUserContextValue>({
  user: null,
  effective: null,
  permissions: EMPTY_PERMS,
  impersonating: false,
  recentlyExpiredImpersonationLabel: null,
  dismissExpiredImpersonation: () => {},
  loading: true,
  error: null,
  refresh: () => {},
  hasRole: () => false,
  hasAnyRole: () => false,
  hasPermission: () => false,
});

interface PermissionsResponse {
  role: string | null;
  permissions: string[];
}

function rank(role: Role | null | undefined): number {
  return role ? (BUILTIN_ROLE_RANK[role] ?? 0) : 0;
}

export function CurrentUserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [permissions, setPermissions] = useState<ReadonlySet<string>>(EMPTY_PERMS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshTick, setRefreshTick] = useState(0);
  // B254 (v0.9.10.0.5): track auto-expiry of impersonation so a toast
  // can fire when the flag flips from set to unset between refreshes.
  const previousActingAsRef = useRef<string | null>(null);
  const previousActingAsLabelRef = useRef<string | null>(null);
  const [recentlyExpiredLabel, setRecentlyExpiredLabel] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    Promise.allSettled([
      apiFetch("/api/auth/me").then((r) => r.ok ? r.json() : null),
      apiFetch("/api/auth/me/permissions").then(
        (r) => r.ok ? (r.json() as Promise<PermissionsResponse>) : null,
      ),
    ])
      .then(([meResult, permsResult]) => {
        if (cancelled) return;
        const me = meResult.status === "fulfilled" ? meResult.value : null;
        const perms = permsResult.status === "fulfilled" ? permsResult.value : null;
        // B254: detect impersonation auto-expiry. If the previous /me
        // had acting_as set and this one doesn't, we surface a toast
        // (the user didn't click Exit; the server cleared the flag
        // because acting_as_until passed).
        const prev = previousActingAsRef.current;
        const newActingAsId = (me as CurrentUser | null)?.acting_as?.id ?? null;
        // Reset previous-actor tracking — the just-finished session
        // doesn't show a toast on its own click-to-exit path because
        // exit() reloads the whole page, blowing away this state.
        // Auto-expiry instead refreshes via refreshTick / polling.
        if (prev && !newActingAsId) {
          // Look for a stashed label of the previously-impersonated user.
          const expiredLabel = previousActingAsLabelRef.current ?? "user";
          setRecentlyExpiredLabel(expiredLabel);
        }
        previousActingAsRef.current = newActingAsId;
        previousActingAsLabelRef.current = (me as CurrentUser | null)?.acting_as
          ? ((me as CurrentUser).acting_as!.name ?? (me as CurrentUser).acting_as!.email)
          : null;

        setUser(me as CurrentUser | null);
        setPermissions(perms ? new Set(perms.permissions) : EMPTY_PERMS);
        setError(null);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : "Could not load user.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [refreshTick]);

  const value = useMemo<CurrentUserContextValue>(() => {
    const impersonating = !!user?.acting_as;
    const effective: EffectiveIdentity | null = user
      ? (user.acting_as
          ? {
              id: user.acting_as.id,
              email: user.acting_as.email,
              name: user.acting_as.name,
              role: user.acting_as.role,
              avatar_url: user.acting_as.avatar_url,
            }
          : {
              id: user.id,
              email: user.email,
              name: user.name,
              role: user.role,
              avatar_url: user.avatar_url,
            })
      : null;

    const effectiveRank = rank(effective?.role);

    return {
      user,
      effective,
      permissions,
      impersonating,
      recentlyExpiredImpersonationLabel: recentlyExpiredLabel,
      dismissExpiredImpersonation: () => setRecentlyExpiredLabel(null),
      loading,
      error,
      refresh: () => setRefreshTick((t) => t + 1),
      hasRole: (target) => effectiveRank >= rank(target),
      hasAnyRole: (...targets) => targets.some((t) => effectiveRank >= rank(t)),
      hasPermission: (permission) => permissions.has(permission),
    };
  }, [user, permissions, loading, error, recentlyExpiredLabel]);

  return (
    <CurrentUserContext.Provider value={value}>
      {children}
    </CurrentUserContext.Provider>
  );
}

export function useCurrentUser(): CurrentUserContextValue {
  return useContext(CurrentUserContext);
}

/**
 * Returns the effective user (target if impersonating, actor otherwise).
 * Use this for permission/role display, sidebar nav gates, avatar/name
 * rendering — anything that should reflect "what is this session
 * currently behaving as."
 *
 * Returns null while the user is still loading or unauthenticated.
 */
export function useEffectiveIdentity(): EffectiveIdentity | null {
  return useContext(CurrentUserContext).effective;
}

/**
 * Returns true iff the session is currently impersonating another user.
 * Components that should render an impersonation banner / "Exit" button
 * key off this.
 */
export function useImpersonating(): boolean {
  return useContext(CurrentUserContext).impersonating;
}
