import { useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { cn } from "@/lib/utils";
import DashboardRenderer from "@/widgets/DashboardRenderer";

const PAGE_LABELS: Record<string, string> = {};

export default function EmbedMultiPage() {
  const { pluginId } = useParams<{ pluginId: string }>();
  const [searchParams] = useSearchParams();

  const pagesParam = searchParams.get("pages") || "";
  const pages = pagesParam.split(",").map((p) => p.trim()).filter(Boolean);
  const [activeTab, setActiveTab] = useState(pages[0] ?? "");

  if (!pluginId) {
    return <p className="text-sm text-muted-foreground p-4">Missing plugin ID</p>;
  }

  if (pages.length <= 1) {
    return (
      <div className="pb-10">
        <DashboardRenderer pluginId={pluginId} dashboardName={pages[0] ?? ""} />
      </div>
    );
  }

  return (
    <div className="pb-10">
      <div className="flex items-center gap-0 border-b border-border mb-4 overflow-x-auto">
        {pages.map((page) => (
          <button
            key={page}
            onClick={() => setActiveTab(page)}
            className={cn(
              "px-4 py-2.5 text-xs font-body border-b-2 transition-colors -mb-[1px] whitespace-nowrap",
              activeTab === page
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            {PAGE_LABELS[page] || page.replace(/-/g, " ")}
          </button>
        ))}
      </div>
      <DashboardRenderer pluginId={pluginId} dashboardName={activeTab} />
    </div>
  );
}
