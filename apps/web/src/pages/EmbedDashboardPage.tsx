import { useParams, useSearchParams } from "react-router-dom";
import DashboardRenderer from "@/widgets/DashboardRenderer";

export default function EmbedDashboardPage() {
  const { pluginId, dashboardName } = useParams<{ pluginId: string; dashboardName: string }>();
  const [searchParams] = useSearchParams();

  if (!pluginId || !dashboardName) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <p className="text-sm text-muted-foreground">Missing plugin or dashboard ID</p>
      </div>
    );
  }

  return (
    <div className="pb-10">
      {searchParams.get("header") !== "false" && (
        <div className="mb-4">
          <h1 className="font-display text-lg text-foreground capitalize">
            {dashboardName.replace(/-/g, " ")}
          </h1>
          <p className="text-xs text-muted-foreground">
            {pluginId} &middot; Live data
          </p>
        </div>
      )}
      <DashboardRenderer pluginId={pluginId} dashboardName={dashboardName} />
    </div>
  );
}
