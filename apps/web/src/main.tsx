import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import "./index.css";
// v0.10.1.0: react-grid-layout CSS for the dashboard builder's drag-and-resize.
import "react-grid-layout/css/styles.css";
import "react-resizable/css/styles.css";
import { PrivacyProvider } from "./lib/privacy";
import { queryClient } from "./lib/queryClient";

// react-grab: dev-only component inspector
// Activate with ⌘+Shift+G (Mac) / Ctrl+Shift+G (Windows)
if (import.meta.env.DEV) {
  let grabLoaded = false;
  window.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === "G" && !grabLoaded) {
      grabLoaded = true;
      import("react-grab");
    }
  });
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <PrivacyProvider>
        <App />
      </PrivacyProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
