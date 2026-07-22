import { defineConfig } from "vitest/config";

// api.test.ts exercises apiFetch's browser behaviour (localStorage,
// window.location) — it needs a DOM. Shipped in v1.0.2 without any
// runner config, so it had never actually run until this landed.
export default defineConfig({
  test: {
    environment: "jsdom",
  },
});
