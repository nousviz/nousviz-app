import { useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { cn } from "@/lib/utils";
import DashboardRenderer from "@/widgets/DashboardRenderer";

export default function CanvasPage() {
  const { pluginId, pageName } = useParams<{ pluginId: string; pageName: string }>();
  const [searchParams] = useSearchParams();

  const pagesParam = searchParams.get("pages");
  const pages = pagesParam ? pagesParam.split(",").map(p => p.trim()).filter(Boolean) : null;

  const [activeTab, setActiveTab] = useState(
    pages ? (pages.includes(pageName ?? "") ? pageName! : pages[0]) : (pageName ?? "")
  );

  if (!pluginId || !pageName) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-sm text-muted-foreground">Missing plugin or page</p>
      </div>
    );
  }

  const showTitle = searchParams.get("title") !== "false";
  const showPoweredBy = searchParams.get("badge") !== "false";
  const customTitle = searchParams.get("heading");
  const customSubtitle = searchParams.get("subtitle");
  const accent = searchParams.get("accent");
  const accentColor = accent ? `#${accent}` : undefined;

  // ── Multi-page (tabbed) canvas ──────────────────────────────────────
  if (pages && pages.length > 1) {
    return (
      <div className="min-h-screen flex flex-col">
        <div className="border-b border-border/40 px-6 pt-4 flex items-end gap-0 overflow-x-auto">
          {showTitle && customTitle && (
            <span
              className="font-display font-semibold text-sm mr-6 mb-2.5 shrink-0"
              style={{ color: accentColor }}
            >
              {customTitle}
            </span>
          )}
          {pages.map(page => (
            <button
              key={page}
              onClick={() => setActiveTab(page)}
              className={cn(
                "px-4 py-2.5 text-xs font-body border-b-2 transition-colors -mb-[1px] whitespace-nowrap shrink-0",
                activeTab === page
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )}
              style={activeTab === page && accentColor ? { borderColor: accentColor, color: "inherit" } : undefined}
            >
              {page.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase())}
            </button>
          ))}
        </div>

        <div className="flex-1 px-8 py-8 max-w-[1400px] mx-auto w-full">
          <DashboardRenderer pluginId={pluginId} dashboardName={activeTab} />
        </div>

        {showPoweredBy && (
          <div className="py-6 text-center border-t border-border/30">
            <a
              href="https://nousviz.com"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              <span className="font-display font-semibold text-primary text-sm">NV</span>
              <span>Powered by</span>
              <span className="font-display font-semibold">NousViz</span>
            </a>
          </div>
        )}
      </div>
    );
  }

  // ── Single-page canvas ──────────────────────────────────────────────
  return (
    <div className="min-h-screen">
      {showTitle && (
        <div className="px-8 pt-12 pb-8 max-w-[1400px] mx-auto">
          <h1
            className="font-display text-3xl md:text-4xl font-semibold mb-2"
            style={{ color: accentColor }}
          >
            {customTitle || pageName.replace(/-/g, " ")}
          </h1>
          {customSubtitle && (
            <p className="text-lg text-muted-foreground font-body">{customSubtitle}</p>
          )}
          <div className="h-px bg-border mt-6" />
        </div>
      )}

      <div className="px-8 pb-12 max-w-[1400px] mx-auto">
        <DashboardRenderer pluginId={pluginId} dashboardName={pageName} />
      </div>

      {showPoweredBy && (
        <div className="py-6 text-center border-t border-border/30">
          <a
            href="https://nousviz.com"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <span className="font-display font-semibold text-primary text-sm">NV</span>
            <span>Powered by</span>
            <span className="font-display font-semibold">NousViz</span>
          </a>
        </div>
      )}
    </div>
  );
}
