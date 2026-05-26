/**
 * Tests for apiFetch's 401 auto-logout scoping.
 *
 * Regression: before v1.0.2, ANY 401 from ANY endpoint triggered apiFetch
 * to wipe localStorage and redirect to login. That meant a single bug on
 * /api/plugins (the v1.0.1 bug) cascaded into a team-wide
 * everyone-is-logged-out outage. The fix narrows auto-logout to fire only
 * on 401s from the canonical session-check endpoints
 * (/api/auth/me, /api/auth/me/permissions).
 */
import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";

// Mock the generated client BEFORE importing api.ts (it imports types from it).
vi.mock("@nousviz/client", () => ({}));

import { _isSessionProbe, apiFetch } from "./api";

describe("_isSessionProbe", () => {
  it("matches /api/auth/me exactly", () => {
    expect(_isSessionProbe("/api/auth/me")).toBe(true);
  });

  it("matches /api/auth/me/permissions exactly", () => {
    expect(_isSessionProbe("/api/auth/me/permissions")).toBe(true);
  });

  it("ignores query strings", () => {
    expect(_isSessionProbe("/api/auth/me?cache=0")).toBe(true);
    expect(_isSessionProbe("/api/auth/me/permissions?_=12345")).toBe(true);
  });

  it("rejects /api/plugins", () => {
    expect(_isSessionProbe("/api/plugins")).toBe(false);
  });

  it("rejects /api/auth/me/avatar (different endpoint under /me/)", () => {
    expect(_isSessionProbe("/api/auth/me/avatar")).toBe(false);
  });

  it("rejects /api/auth/login", () => {
    expect(_isSessionProbe("/api/auth/login")).toBe(false);
  });

  it("rejects unrelated plugin sub-routes", () => {
    expect(_isSessionProbe("/api/plugins/avizo-jira/dashboards/overview")).toBe(false);
    expect(_isSessionProbe("/api/plugins/intercom/sync-schedule")).toBe(false);
  });

  it("handles absolute URLs", () => {
    expect(_isSessionProbe("https://statsdrone.nousviz.app/api/auth/me")).toBe(true);
    expect(_isSessionProbe("https://statsdrone.nousviz.app/api/plugins")).toBe(false);
  });

  it("handles URL objects", () => {
    expect(_isSessionProbe(new URL("https://example.test/api/auth/me"))).toBe(true);
    expect(_isSessionProbe(new URL("https://example.test/api/plugins"))).toBe(false);
  });

  it("handles Request objects", () => {
    const req = new Request("https://example.test/api/auth/me");
    expect(_isSessionProbe(req)).toBe(true);
    const req2 = new Request("https://example.test/api/plugins");
    expect(_isSessionProbe(req2)).toBe(false);
  });
});

describe("apiFetch — 401 auto-logout is scoped to session-check endpoints", () => {
  const TOKEN_KEY = "nousviz_auth_token";
  const ORIGINAL_LOCATION = window.location;

  beforeEach(() => {
    localStorage.setItem(TOKEN_KEY, "test-token-abc");
    // Make window.location.href assignable so we can detect redirects.
    Object.defineProperty(window, "location", {
      writable: true,
      value: {
        ...ORIGINAL_LOCATION,
        pathname: "/some/page",
        href: "http://test.local/some/page",
      },
    });
  });

  afterEach(() => {
    localStorage.removeItem(TOKEN_KEY);
    Object.defineProperty(window, "location", {
      writable: true,
      value: ORIGINAL_LOCATION,
    });
    vi.restoreAllMocks();
  });

  function mockFetchOnceWith(status: number, bodyJson: unknown = {}) {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(bodyJson), {
        status,
        headers: { "Content-Type": "application/json" },
      }),
    );
  }

  it("401 from /api/plugins does NOT clear token or redirect (THE FIX)", async () => {
    mockFetchOnceWith(401, { detail: "boom" });
    const res = await apiFetch("/api/plugins");
    expect(res.status).toBe(401);
    expect(localStorage.getItem(TOKEN_KEY)).toBe("test-token-abc");
    expect(window.location.href).toBe("http://test.local/some/page");
  });

  it("401 from /api/plugins/avizo-jira/anything does NOT clear token", async () => {
    mockFetchOnceWith(401);
    await apiFetch("/api/plugins/avizo-jira/sync-schedule");
    expect(localStorage.getItem(TOKEN_KEY)).toBe("test-token-abc");
  });

  it("401 from /api/auth/me DOES clear token + redirect", async () => {
    mockFetchOnceWith(401, { detail: "Not authenticated" });
    await apiFetch("/api/auth/me");
    expect(localStorage.getItem(TOKEN_KEY)).toBe(null);
    expect(window.location.href).toContain("/?return=");
  });

  it("401 from /api/auth/me/permissions DOES clear token + redirect", async () => {
    mockFetchOnceWith(401, { detail: "Not authenticated" });
    await apiFetch("/api/auth/me/permissions");
    expect(localStorage.getItem(TOKEN_KEY)).toBe(null);
  });

  it("200 from any endpoint never touches token or redirects", async () => {
    mockFetchOnceWith(200, { plugins: [] });
    await apiFetch("/api/plugins");
    expect(localStorage.getItem(TOKEN_KEY)).toBe("test-token-abc");
    expect(window.location.href).toBe("http://test.local/some/page");
  });

  it("401 with no token in localStorage is a no-op (cannot 'clear' nothing)", async () => {
    localStorage.removeItem(TOKEN_KEY);
    mockFetchOnceWith(401);
    await apiFetch("/api/auth/me");
    // No assertions on redirect — the guard `&& token` prevents the redirect.
    expect(window.location.href).toBe("http://test.local/some/page");
  });

  it("/shared/ paths bypass the auto-logout even on auth/me 401", async () => {
    Object.defineProperty(window, "location", {
      writable: true,
      value: {
        ...ORIGINAL_LOCATION,
        pathname: "/shared/abc123",
        href: "http://test.local/shared/abc123",
      },
    });
    mockFetchOnceWith(401);
    await apiFetch("/api/auth/me");
    expect(localStorage.getItem(TOKEN_KEY)).toBe("test-token-abc");
  });
});
