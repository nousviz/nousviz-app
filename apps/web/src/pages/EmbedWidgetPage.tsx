import { useParams } from "react-router-dom";
import { useState, useEffect } from "react";
import { query, getDashboardSpec } from "@/lib/api";
import ChartWidget from "@/widgets/ChartWidget";
import KpiWidget from "@/widgets/KpiWidget";
import TableWidget from "@/widgets/TableWidget";

export default function EmbedWidgetPage() {
  const { pluginId, dashboardName, widgetIndex } = useParams<{
    pluginId: string;
    dashboardName: string;
    widgetIndex: string;
  }>();
  const [widgetData, setWidgetData] = useState<Record<string, unknown>[] | null>(null);
  const [widgetSpec, setWidgetSpec] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      if (!pluginId || !dashboardName || widgetIndex == null) return;

      try {
        setLoading(true);
        const spec = await getDashboardSpec(pluginId, dashboardName);
        const idx = parseInt(widgetIndex);
        const widget = (spec as any).widgets?.[idx];

        if (!widget) {
          setError(`Widget ${widgetIndex} not found`);
          return;
        }

        setWidgetSpec(widget);

        // Build and execute query
        const c = widget.config;
        const dataset = c.dataset;
        if (!dataset) return;

        let sql = "";
        const period = (c.period as string) || "30d";
        const days = parseInt(period) || 30;

        if (widget.type === "kpi") {
          const expression = c.expression || `sum(${c.metric})`;
          sql = `SELECT ${expression} as value FROM ${dataset} FINAL WHERE date >= today() - ${days}`;
        } else if (widget.type.includes("chart")) {
          const x = c.x;
          const y = Array.isArray(c.y) ? c.y : [c.y];
          if (x === "date") {
            const selects = y.map((col: string) => `sum(${col}) as ${col}`).join(", ");
            sql = `SELECT date, ${selects} FROM ${dataset} FINAL WHERE date >= today() - ${days} GROUP BY date ORDER BY date`;
          } else {
            sql = `SELECT ${x}, sum(${y[0]}) as ${y[0]} FROM ${dataset} FINAL WHERE date >= today() - ${days} GROUP BY ${x} ORDER BY ${y[0]} DESC LIMIT ${c.limit || 20}`;
          }
        } else if (widget.type === "table") {
          const columns = c.columns as any[];
          const groupBy = Array.isArray(c.group_by) ? c.group_by : c.group_by ? [c.group_by] : [];
          const selects = columns.map((col: any) => {
            if (col.expression) return `${col.expression} as ${col.field}`;
            if (groupBy.includes(col.field)) return col.field;
            return `sum(${col.field}) as ${col.field}`;
          });
          sql = `SELECT ${selects.join(", ")} FROM ${dataset} FINAL WHERE date >= today() - ${days}`;
          if (groupBy.length) sql += ` GROUP BY ${groupBy.join(", ")}`;
          if (c.sort_by) sql += ` ORDER BY ${c.sort_by} ${(c.sort_dir || "desc").toUpperCase()}`;
          sql += ` LIMIT ${c.limit || 20}`;
        }

        if (sql) {
          const result = await query(sql);
          setWidgetData(result.rows);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load widget");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [pluginId, dashboardName, widgetIndex]);

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[200px]">
        <p className="text-sm text-red-400">{error}</p>
      </div>
    );
  }

  if (!widgetSpec || loading) {
    return (
      <div className="bg-card rounded-lg border border-border p-5 animate-pulse">
        <div className="h-[250px] bg-secondary/30 rounded" />
      </div>
    );
  }

  const c = widgetSpec.config;

  if (widgetSpec.type === "kpi") {
    return (
      <div className="pb-8">
        <KpiWidget
          label={c.label || ""}
          value={widgetData?.[0]?.value != null ? Number(widgetData[0].value) : 0}
          format={c.format}
          loading={false}
        />
      </div>
    );
  }

  if (widgetSpec.type.includes("chart")) {
    const x = c.x;
    const y = Array.isArray(c.y) ? c.y : [c.y];
    const chartType = widgetSpec.type === "line_chart" ? "line" : widgetSpec.type === "stacked_bar_chart" ? "stacked_bar" : "bar";
    const chartData = (widgetData || []).map((row) => ({
      ...row,
      [x]: x === "date" && typeof row[x] === "string" ? (row[x] as string).slice(5) : row[x],
    }));

    return (
      <div className="pb-8">
        <ChartWidget
          title={c.title}
          type={chartType}
          data={chartData}
          xKey={x}
          yKeys={y}
          yLabels={c.labels}
          loading={false}
        />
      </div>
    );
  }

  if (widgetSpec.type === "table") {
    return (
      <div className="pb-8">
        <TableWidget
          title={c.title}
          columns={c.columns || []}
          rows={widgetData || []}
          loading={false}
        />
      </div>
    );
  }

  return <p className="text-sm text-muted-foreground">Unsupported widget type: {widgetSpec.type}</p>;
}
