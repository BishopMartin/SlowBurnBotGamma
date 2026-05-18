import { NextResponse } from "next/server";
import fs from "node:fs";
import path from "node:path";
import { loadTheme } from "@/lib/theme-loader";

const PREVIEW_SLOTS = ["base00","base08","base0A","base0B","base0E","base05"];

export function GET() {
  const dir = path.join(process.cwd(), "themes");
  const slugs = fs.readdirSync(dir)
    .filter((f) => f.endsWith(".yaml"))
    .map((f) => f.replace(".yaml", ""))
    .sort();

  const themes = slugs.map((slug) => {
    const t = loadTheme(slug);
    const preview = Object.fromEntries(
      PREVIEW_SLOTS.map((s) => [s, `#${(t.palette[s] ?? t.palette[s.toUpperCase()] ?? "000000").replace(/^#/, "")}`])
    );
    return { slug, name: t.name, preview };
  });

  return NextResponse.json(themes);
}
