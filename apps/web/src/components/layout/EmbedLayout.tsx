import { useEffect } from "react";
import { Outlet, useSearchParams } from "react-router-dom";

export default function EmbedLayout() {
  const [searchParams] = useSearchParams();
  const theme = searchParams.get("theme");
  const noBadge = searchParams.get("badge") === "false";

  // Apply theme from query param, overriding localStorage
  useEffect(() => {
    const root = document.documentElement;
    if (theme === "light") {
      root.classList.remove("dark");
      root.classList.add("light");
    } else if (theme === "dark") {
      root.classList.remove("light");
      root.classList.add("dark");
    }
    // If no theme param, inherit whatever the app has set
  }, [theme]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="p-4">
        <Outlet />
      </div>
      {/* Powered by badge — hide with ?badge=false (paid tier) */}
      {!noBadge && <div className="fixed bottom-0 left-0 right-0 flex justify-center py-2 bg-gradient-to-t from-background/90 to-transparent pointer-events-none">
        <a
          href="https://nousviz.com"
          target="_blank"
          rel="noopener noreferrer"
          className="pointer-events-auto flex items-center gap-1.5 px-3 py-1 rounded-full bg-card/80 border border-border/50 backdrop-blur-sm text-[10px] text-muted-foreground hover:text-foreground transition-colors"
        >
          <span className="font-display font-semibold text-primary text-[11px]">NV</span>
          <span>Built with</span>
          <span className="font-display font-semibold">NousViz</span>
        </a>
      </div>}
    </div>
  );
}
