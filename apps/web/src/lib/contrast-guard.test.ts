/**
 * B340 (v1.0.7): keep low-contrast text classes out of the web app.
 *
 * Palette text shades 100-400 (`text-blue-300`, `text-red-400`, ...) were
 * picked for dark backgrounds and read at 1.1-2.8:1 on white. Status text
 * uses the theme tokens instead (`text-info-foreground`,
 * `text-success-foreground`, `text-warning-foreground`,
 * `text-danger-foreground`), which reach 4.5:1 in every palette. A category
 * colour may keep its hue with a light-mode shade and a `dark:` pair
 * (`text-purple-700 dark:text-purple-300`). A line that genuinely needs a
 * pale shade (a chart colour, say) can carry `contrast-ok: <reason>`.
 *
 * Run: npx vitest run src/lib/contrast-guard.test.ts
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, it } from "vitest";

const SRC = join(__dirname, "..");
const HUES =
  "blue|green|amber|red|yellow|emerald|sky|cyan|orange|purple|violet|rose|teal|lime|indigo|pink|fuchsia";
// A bare text shade 100-400, with any variant prefix except dark:.
const PALE = new RegExp(`(?<![\\w-])((?:[a-z-]+:)*)text-(${HUES})-(100|200|300|400)(?![\\w-])`, "g");

export function paleClasses(line: string): string[] {
  if (line.includes("contrast-ok:")) return [];
  const out: string[] = [];
  for (const m of line.matchAll(PALE)) {
    if (!m[1].split(":").includes("dark")) out.push(m[0]);
  }
  return out;
}

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) return name === "node_modules" ? [] : files(p);
    return /\.(tsx|ts)$/.test(name) && !/\.test\.tsx?$/.test(name) ? [p] : [];
  });
}

describe("contrast guard (B340)", () => {
  it("flags a bare pale shade and accepts tokens, dark: pairs and marked lines", () => {
    expect(paleClasses('<span className="text-blue-300">x</span>')).toEqual(["text-blue-300"]);
    expect(paleClasses('className="text-red-400 hover:text-red-300"')).toEqual(["text-red-400", "hover:text-red-300"]);
    expect(paleClasses('className="text-info-foreground hover:opacity-80"')).toEqual([]);
    expect(paleClasses('className="text-purple-700 dark:text-purple-300"')).toEqual([]);
    expect(paleClasses('className="text-red-700 dark:hover:text-red-300"')).toEqual([]);
    expect(paleClasses('stroke="text-sky-400" // contrast-ok: chart colour')).toEqual([]);
    expect(paleClasses('className="text-blue-500 text-red-700"')).toEqual([]);
  });

  it("no source file uses a bare pale text shade", () => {
    const hits: string[] = [];
    for (const f of files(SRC)) {
      readFileSync(f, "utf8").split("\n").forEach((line, i) => {
        for (const c of paleClasses(line)) hits.push(`${relative(SRC, f)}:${i + 1}  ${c}`);
      });
    }
    expect(hits, `Use text-{info,success,warning,danger}-foreground (or a dark: pair):\n${hits.join("\n")}`).toEqual([]);
  });
});
