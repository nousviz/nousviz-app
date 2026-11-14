/**
 * B348: withStepUp(fetchFn) — shows the host step-up prompt on a 401
 * `stepup_required` and retries the wrapped call once.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";

vi.mock("@nousviz/client", () => ({}));

import { withStepUp, retryStepUpRequest, cancelStepUpRequest } from "./api";

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const STEPUP = { detail: { error: "stepup_required", message: "x" } };

describe("withStepUp", () => {
  let events: boolean[];

  beforeEach(() => {
    events = [];
    window.addEventListener("nousviz:stepup-required", (e) => {
      events.push(!!(e as CustomEvent<{ pending: boolean }>).detail?.pending);
    });
  });

  it("passes non-step-up responses straight through", async () => {
    const fn = vi.fn(async () => json(200, { ok: true }));
    const res = await withStepUp(fn)("/api/x", { method: "POST" });
    expect(res.status).toBe(200);
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it("prompts, then retries once after a successful step-up", async () => {
    const fn = vi
      .fn()
      .mockResolvedValueOnce(json(401, STEPUP))
      .mockResolvedValueOnce(json(200, { value: "s" }));
    const pending = withStepUp(fn)("/api/x", { method: "POST" });
    await new Promise((r) => setTimeout(r, 0));
    expect(events).toContain(true); // modal asked to open
    retryStepUpRequest(); // what StepUpController does on a correct password
    const res = await pending;
    expect(res.status).toBe(200);
    expect(fn).toHaveBeenCalledTimes(2);
    expect(fn).toHaveBeenLastCalledWith("/api/x", { method: "POST" });
  });

  it("retries only once: a second stepup_required is returned", async () => {
    const fn = vi.fn(async () => json(401, STEPUP));
    const pending = withStepUp(fn)("/api/x");
    await new Promise((r) => setTimeout(r, 0));
    retryStepUpRequest();
    const res = await pending;
    expect(res.status).toBe(401);
    expect(fn).toHaveBeenCalledTimes(2);
  });

  it("resolves with stepup_cancelled when the user cancels", async () => {
    const fn = vi.fn(async () => json(401, STEPUP));
    const pending = withStepUp(fn)("/api/x");
    await new Promise((r) => setTimeout(r, 0));
    cancelStepUpRequest();
    const res = await pending;
    expect(res.status).toBe(401);
    expect((await res.json()).detail.error).toBe("stepup_cancelled");
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it("does not prompt for an ordinary 401", async () => {
    const fn = vi.fn(async () => json(401, { detail: "Authentication required." }));
    const res = await withStepUp(fn)("/api/x");
    expect(res.status).toBe(401);
    expect(events).not.toContain(true);
  });
});
