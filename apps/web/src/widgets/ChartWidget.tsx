import { useRef, useState } from "react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { MoreHorizontal, Image, FileCode, FileSpreadsheet, Link2 } from "lucide-react";

const COLORS = ["#3b82f6", "#22c55e", "#f59e0b", "#8b5cf6", "#ef4444", "#06b6d4"];

interface ChartWidgetProps {
  title?: string;
  type: "line" | "bar" | "stacked_bar";
  data: Record<string, unknown>[];
  xKey: string;
  yKeys: string[];
  yLabels?: string[];
  loading?: boolean;
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload) return null;
  return (
    <div className="bg-card border border-border rounded-md px-3 py-2 shadow-lg">
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      {payload.map((entry: any, i: number) => (
        <p key={i} className="text-xs font-mono-deck" style={{ color: entry.color }}>
          {entry.name}: {typeof entry.value === "number" ? entry.value.toLocaleString() : entry.value}
        </p>
      ))}
    </div>
  );
}

// ── Export utilities ──────────────────────────────────────────────────

function getSvgElement(container: HTMLElement): SVGSVGElement | null {
  return container.querySelector("svg.recharts-surface");
}

function downloadSvg(container: HTMLElement, filename: string) {
  const svg = getSvgElement(container);
  if (!svg) return;

  // Clone and add white/transparent background
  const clone = svg.cloneNode(true) as SVGSVGElement;
  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");

  const blob = new Blob([clone.outerHTML], { type: "image/svg+xml" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${filename}.svg`;
  a.click();
  URL.revokeObjectURL(url);
}

function downloadPng(container: HTMLElement, filename: string) {
  const svg = getSvgElement(container);
  if (!svg) return;

  const clone = svg.cloneNode(true) as SVGSVGElement;
  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");

  const svgData = new XMLSerializer().serializeToString(clone);
  const canvas = document.createElement("canvas");
  const rect = svg.getBoundingClientRect();
  const scale = 2; // 2x for retina
  canvas.width = rect.width * scale;
  canvas.height = rect.height * scale;
  const ctx = canvas.getContext("2d")!;
  ctx.scale(scale, scale);

  const img = new window.Image();
  img.onload = () => {
    // Dark background
    ctx.fillStyle = "#0f0f1a";
    ctx.fillRect(0, 0, rect.width, rect.height);
    ctx.drawImage(img, 0, 0, rect.width, rect.height);
    canvas.toBlob((blob) => {
      if (!blob) return;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${filename}.png`;
      a.click();
      URL.revokeObjectURL(url);
    }, "image/png");
  };
  img.src = `data:image/svg+xml;base64,${btoa(unescape(encodeURIComponent(svgData)))}`;
}

function downloadCsv(data: Record<string, unknown>[], xKey: string, yKeys: string[], filename: string) {
  const columns = [xKey, ...yKeys];
  const header = columns.join(",");
  const body = data
    .map((row) =>
      columns.map((col) => {
        const val = row[col];
        if (val == null) return "";
        const str = String(val);
        return str.includes(",") ? `"${str}"` : str;
      }).join(",")
    )
    .join("\n");

  const blob = new Blob([header + "\n" + body], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${filename}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function copyEmbedLink() {
  // Build embed URL from the current page path
  // e.g., /plugin/starter-plugin/analytics → /embed/dashboard/starter-plugin/analytics
  const path = window.location.pathname;
  const match = path.match(/\/plugin\/([^/]+)\/dashboards\/([^/]+)/);
  let url: string;
  if (match) {
    url = `${window.location.origin}/embed/dashboard/${match[1]}/${match[2]}`;
  } else {
    url = `${window.location.origin}/embed${path}`;
  }
  navigator.clipboard.writeText(url);
}

// ── Chart menu ───────────────────────────────────────────────────────

function ChartMenu({
  containerRef,
  title,
  data,
  xKey,
  yKeys,
}: {
  containerRef: React.RefObject<HTMLDivElement | null>;
  title: string;
  data: Record<string, unknown>[];
  xKey: string;
  yKeys: string[];
}) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const filename = (title || "chart").toLowerCase().replace(/\s+/g, "_");

  const handleAction = (action: () => void) => {
    action();
    setOpen(false);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="h-7 w-7 rounded-md flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
      >
        <MoreHorizontal className="w-4 h-4" />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-8 z-50 w-48 bg-card border border-border rounded-lg shadow-xl py-1">
            <button
              onClick={() => handleAction(() => containerRef.current && downloadPng(containerRef.current, filename))}
              className="w-full px-3 py-2 text-xs text-foreground hover:bg-secondary flex items-center gap-2 transition-colors text-left"
            >
              <Image className="w-3.5 h-3.5 text-muted-foreground" />
              Download PNG
            </button>
            <button
              onClick={() => handleAction(() => containerRef.current && downloadSvg(containerRef.current, filename))}
              className="w-full px-3 py-2 text-xs text-foreground hover:bg-secondary flex items-center gap-2 transition-colors text-left"
            >
              <FileCode className="w-3.5 h-3.5 text-muted-foreground" />
              Download SVG
            </button>
            <button
              onClick={() => handleAction(() => downloadCsv(data, xKey, yKeys, filename))}
              className="w-full px-3 py-2 text-xs text-foreground hover:bg-secondary flex items-center gap-2 transition-colors text-left"
            >
              <FileSpreadsheet className="w-3.5 h-3.5 text-muted-foreground" />
              Export CSV
            </button>
            <div className="h-px bg-border my-1" />
            <button
              onClick={() => {
                copyEmbedLink();
                setCopied(true);
                setTimeout(() => setCopied(false), 2000);
                setOpen(false);
              }}
              className="w-full px-3 py-2 text-xs text-foreground hover:bg-secondary flex items-center gap-2 transition-colors text-left"
            >
              <Link2 className="w-3.5 h-3.5 text-muted-foreground" />
              {copied ? "Copied!" : "Copy Embed Link"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────

export default function ChartWidget({ title, type, data, xKey, yKeys, yLabels, loading }: ChartWidgetProps) {
  const chartRef = useRef<HTMLDivElement>(null);

  if (loading) {
    return (
      <div className="bg-card rounded-lg border border-border p-5 animate-pulse">
        {title && <div className="h-4 w-32 bg-secondary rounded mb-4" />}
        <div className="h-[250px] bg-secondary/30 rounded" />
      </div>
    );
  }

  const labels = yLabels || yKeys;

  return (
    <div className="bg-card rounded-lg border border-border p-5 group relative">
      {/* Header with menu */}
      <div className="flex items-center justify-between mb-4">
        {title && <h3 className="font-display text-sm text-foreground">{title}</h3>}
        <div className="opacity-0 group-hover:opacity-100 transition-opacity">
          <ChartMenu
            containerRef={chartRef}
            title={title || "chart"}
            data={data}
            xKey={xKey}
            yKeys={yKeys}
          />
        </div>
      </div>

      {/* Chart */}
      {/* B159 (v0.9.4.8): Recharts' default cursor (the on-hover bar/area
          highlight) and Tooltip wrapper paint white-ish backgrounds that
          clash with the dark theme. Tooltip we already replace via
          `content={<CustomTooltip />}`, but `cursor` is a separate prop —
          its default is a near-white fill that produces the "white box"
          effect on bar charts during hover. Override to a subtle
          translucent white. Same on line charts (cursor is a vertical
          line; default stroke also pale). */}
      <div ref={chartRef}>
        <ResponsiveContainer width="100%" height={250}>
          {type === "line" ? (
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey={xKey} tick={{ fontSize: 11, fill: "#6b7280" }} />
              <YAxis tick={{ fontSize: 11, fill: "#6b7280" }} />
              <Tooltip
                content={<CustomTooltip />}
                cursor={{ stroke: "rgba(255,255,255,0.15)", strokeWidth: 1 }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              {yKeys.map((key, i) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  name={labels[i]}
                  stroke={COLORS[i % COLORS.length]}
                  strokeWidth={2}
                  dot={false}
                />
              ))}
            </LineChart>
          ) : (
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey={xKey} tick={{ fontSize: 11, fill: "#6b7280" }} />
              <YAxis tick={{ fontSize: 11, fill: "#6b7280" }} />
              <Tooltip
                content={<CustomTooltip />}
                cursor={{ fill: "rgba(255,255,255,0.04)" }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              {yKeys.map((key, i) => (
                <Bar
                  key={key}
                  dataKey={key}
                  name={labels[i]}
                  fill={COLORS[i % COLORS.length]}
                  stackId={type === "stacked_bar" ? "stack" : undefined}
                  radius={type === "stacked_bar" ? undefined : [4, 4, 0, 0]}
                />
              ))}
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
