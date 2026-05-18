import SidebarLogo from "./SidebarLogo";

/**
 * Boot splash shown by AuthGate while the auth check + plugin frontend
 * loader resolve. The wordmark wipes in left-to-right on a loop so the
 * user sees an obvious "loading" signal rather than a static logo.
 *
 * The animation uses a CSS clip-path on a wrapper around SidebarLogo —
 * the logo SVG itself is unmodified, so the sidebar's normal rendering
 * is unaffected.
 */
export default function BootSplash() {
  const instanceName =
    typeof window !== "undefined"
      ? localStorage.getItem("nousviz:instance_name") || ""
      : "";

  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <style>{`
        @keyframes nv-boot-pulse {
          0%, 100% { opacity: 1; }
          50%      { opacity: 0.45; }
        }
        .nv-boot-pulse {
          animation: nv-boot-pulse 1.6s ease-in-out infinite;
        }
      `}</style>
      <div className="flex flex-col items-center gap-4">
        <div className="nv-boot-pulse">
          <SidebarLogo collapsed={false} />
        </div>
        {instanceName && (
          <div className="text-xs font-mono-deck text-muted-foreground tracking-wide">
            {instanceName}
          </div>
        )}
      </div>
    </div>
  );
}
