import { useEffect } from "react";
import { Outlet, useSearchParams } from "react-router-dom";

export default function CanvasLayout() {
  const [searchParams] = useSearchParams();
  const theme = searchParams.get("theme");
  const bg = searchParams.get("bg");
  const fg = searchParams.get("fg");
  const accent = searchParams.get("accent");
  const font = searchParams.get("font");

  useEffect(() => {
    const root = document.documentElement;

    // Theme class
    if (theme === "light") {
      root.classList.remove("dark");
      root.classList.add("light");
    } else if (theme === "dark" || !theme) {
      root.classList.remove("light");
      root.classList.add("dark");
    }

    // Custom CSS overrides via URL params
    if (bg) root.style.setProperty("--canvas-bg", `#${bg}`);
    if (fg) root.style.setProperty("--canvas-fg", `#${fg}`);
    if (accent) root.style.setProperty("--canvas-accent", `#${accent}`);
    if (font) root.style.setProperty("--canvas-font", font);

    return () => {
      root.style.removeProperty("--canvas-bg");
      root.style.removeProperty("--canvas-fg");
      root.style.removeProperty("--canvas-accent");
      root.style.removeProperty("--canvas-font");
    };
  }, [theme, bg, fg, accent, font]);

  return (
    <div
      className="min-h-screen text-foreground"
      style={{
        backgroundColor: bg ? `#${bg}` : undefined,
        color: fg ? `#${fg}` : undefined,
        fontFamily: font || undefined,
      }}
    >
      <Outlet />
    </div>
  );
}
