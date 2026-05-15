import type { Metadata } from "next";
import Link from "next/link";
import { Bracket } from "@/lib/bracket";
import { loadTheme } from "@/lib/theme-loader";
import { ACTIVE_THEME } from "@/lib/active-theme";

export const metadata: Metadata = {
  title: "Colors — SlowBurnBot",
  description: "Frontend color palette reference",
};

// Our site-specific names and roles per slot
const SITE_INFO: Record<string, { name: string; role: string }> = {
  base00: { name: "charcoal bg",      role: "Page background  —  --background" },
  base01: { name: "header bar",       role: "Section headers, table strips" },
  base02: { name: "panel",            role: "Select option bg, row hovers, panels" },
  base03: { name: "border taupe",     role: "Borders, dividers, disabled text" },
  base04: { name: "muted text",       role: "Secondary / meta text" },
  base05: { name: "ivory text",       role: "Primary text  —  --foreground" },
  base06: { name: "—",                role: "reserved" },
  base07: { name: "white",            role: "Nav/tab hover" },
  base08: { name: "ember red",        role: "Error / destructive  —  --status-bad" },
  base09: { name: "terracotta",       role: "Links, CTAs, focus rings, accent" },
  base0A: { name: "wheat",            role: "Counts, tokens, warm highlights" },
  base0B: { name: "chartreuse",       role: "Success  —  --status-ok" },
  base0C: { name: "—",                role: "reserved" },
  base0D: { name: "—",                role: "reserved" },
  base0E: { name: "—",                role: "reserved" },
  base0F: { name: "—",                role: "reserved" },
  base10: { name: "—",                role: "reserved" },
  base11: { name: "dropdown hover",   role: "Dropdown row hover" },
  base12: { name: "coral hover",      role: "Bad control hover  —  --status-bad-hover" },
  base13: { name: "—",                role: "reserved" },
  base14: { name: "—",                role: "reserved" },
  base15: { name: "—",                role: "reserved" },
  base16: { name: "—",                role: "reserved" },
  base17: { name: "—",                role: "reserved" },
};

// base24 spec roles
const BASE24_SPEC: Record<string, { name: string; role: string }> = {
  base00: { name: "Default Background",   role: "Background" },
  base01: { name: "Lighter Background",   role: "Status bars, line numbers" },
  base02: { name: "Selection Background", role: "Selection background" },
  base03: { name: "Comments",             role: "Comments, invisibles, line highlighting" },
  base04: { name: "Dark Foreground",      role: "Dark foreground (status bars)" },
  base05: { name: "Default Foreground",   role: "Default foreground, caret, delimiters" },
  base06: { name: "Light Foreground",     role: "Light foreground (rarely used)" },
  base07: { name: "Light Background",     role: "Light background (rarely used)" },
  base08: { name: "Red",                  role: "Variables, XML tags, diff deleted" },
  base09: { name: "Orange",              role: "Integers, booleans, constants, attributes" },
  base0A: { name: "Yellow",              role: "Classes, bold, search text background" },
  base0B: { name: "Green",              role: "Strings, inherited class, diff inserted" },
  base0C: { name: "Cyan",               role: "Support, regex, escape characters" },
  base0D: { name: "Blue",               role: "Functions, methods, headings" },
  base0E: { name: "Purple",             role: "Keywords, storage, selector, italic" },
  base0F: { name: "Brown",              role: "Deprecated, embedded language tags" },
  base10: { name: "Darker Background",   role: "Darker background" },
  base11: { name: "Brighter Background", role: "Brighter background" },
  base12: { name: "Bright Red",          role: "Bright red" },
  base13: { name: "Bright Yellow",       role: "Bright yellow / orange" },
  base14: { name: "Bright Green",        role: "Bright green" },
  base15: { name: "Bright Cyan",         role: "Bright cyan" },
  base16: { name: "Bright Blue",         role: "Bright blue" },
  base17: { name: "Bright Purple",       role: "Bright purple / magenta" },
};

const SECTIONS: Array<{ label: string; slots: string[] }> = [
  { label: "MONOTONES",  slots: ["base00", "base01", "base02", "base03", "base04", "base05", "base06", "base07"] },
  { label: "ACCENTS",    slots: ["base08", "base09", "base0A", "base0B", "base0C", "base0D", "base0E", "base0F"] },
  { label: "EXTENSIONS", slots: ["base10", "base11"] },
  { label: "BRIGHTS",    slots: ["base12", "base13", "base14", "base15", "base16", "base17"] },
];

type Palette = Record<string, string>;

function ph(palette: Palette, slot: string): string {
  return `#${palette[slot]?.replace(/^#/, "") ?? "000000"}`;
}

const GRID = "5.5rem 8.5rem 9rem 1fr";

function PanelHeader({ palette, themeName }: { palette: Palette; themeName: string }) {
  return (
    <div style={{ backgroundColor: ph(palette, "base01"), borderBottom: `1px solid ${ph(palette, "base03")}` }}>
      <div style={{ padding: "6px 12px", color: ph(palette, "base09"), fontWeight: 600, fontSize: "0.8rem", borderBottom: `1px solid ${ph(palette, "base03")}` }}>
        {themeName}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: GRID }}>
        {["slot", "hex", "name", "role"].map((h) => (
          <div key={h} style={{ padding: "3px 12px", color: ph(palette, "base03"), fontSize: "0.7rem" }}>{h}</div>
        ))}
      </div>
    </div>
  );
}

function PanelRow({
  palette,
  slotId,
  name,
  role,
  last,
}: {
  palette: Palette;
  slotId: string;
  name: string;
  role: string;
  last: boolean;
}) {
  const slotHex = ph(palette, slotId);
  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: GRID,
      backgroundColor: ph(palette, "base00"),
      borderBottom: last ? "none" : `1px solid ${ph(palette, "base03")}`,
    }}>
      <div style={{ padding: "6px 12px", color: ph(palette, "base05"), fontSize: "0.8rem" }}>{slotId}</div>
      <div style={{ padding: "6px 12px", display: "flex", alignItems: "center", gap: "6px" }}>
        <div style={{ width: "16px", height: "16px", backgroundColor: slotHex, border: `1px solid ${ph(palette, "base03")}`, borderRadius: "2px", flexShrink: 0 }} />
        <span style={{ color: ph(palette, "base04"), fontSize: "0.75rem" }}>{slotHex}</span>
      </div>
      <div style={{ padding: "6px 12px", color: ph(palette, "base05"), fontSize: "0.8rem" }}>{name}</div>
      <div style={{ padding: "6px 12px", color: ph(palette, "base04"), fontSize: "0.8rem" }}>{role}</div>
    </div>
  );
}

function ThemePanel({
  palette,
  themeName,
  slots,
  getInfo,
}: {
  palette: Palette;
  themeName: string;
  slots: string[];
  getInfo: (slotId: string) => { name: string; role: string };
}) {
  return (
    <div style={{ backgroundColor: ph(palette, "base00"), border: `1px solid ${ph(palette, "base03")}`, overflow: "hidden", minWidth: "420px" }}>
      <PanelHeader palette={palette} themeName={themeName} />
      {slots.map((slotId, i) => {
        const info = getInfo(slotId);
        return (
          <PanelRow
            key={slotId}
            palette={palette}
            slotId={slotId}
            name={info.name}
            role={info.role}
            last={i === slots.length - 1}
          />
        );
      })}
    </div>
  );
}

export default function ColorsPage() {
  const defaultTheme = loadTheme("slowburnbot");
  const activeTheme  = loadTheme(ACTIVE_THEME);

  return (
    <div className="min-h-screen flex flex-col font-mono text-sm">
      <div className="flex-1 max-w-screen-2xl mx-auto w-full sm:border-x border-base03">
        <header className="px-3 sm:px-6 py-3 flex flex-wrap items-baseline gap-x-4 gap-y-2 border-b border-base03">
          <span className="font-semibold text-base09">SlowBurnBot</span>
          <span className="text-base04">colors</span>
          <span className="text-base03 hidden sm:inline">—</span>
          <Link href="/login" className="text-base04 hover:text-base09 transition-colors">
            <Bracket className="">sign in</Bracket>
          </Link>
          <Link href="/dashboard" className="text-base04 hover:text-base09 transition-colors">
            <Bracket className="">dashboard</Bracket>
          </Link>
        </header>

        <main className="px-3 sm:px-6 py-6 space-y-8">
          <p className="text-base04">
            Active theme: <code className="text-base0a">{ACTIVE_THEME}</code>
            {" — "} default: <code className="text-base04">slowburnbot</code>
          </p>

          {SECTIONS.map(({ label, slots }) => (
            <section key={label}>
              <h2 className="text-base04 mb-3 text-xs">{label}</h2>
              <div className="overflow-x-auto">
                <div className="grid grid-cols-2 gap-4" style={{ minWidth: "860px" }}>
                  <ThemePanel
                    palette={defaultTheme.palette}
                    themeName={defaultTheme.name}
                    slots={slots}
                    getInfo={(s) => SITE_INFO[s] ?? { name: "—", role: "reserved" }}
                  />
                  <ThemePanel
                    palette={activeTheme.palette}
                    themeName={activeTheme.name}
                    slots={slots}
                    getInfo={(s) => BASE24_SPEC[s] ?? { name: "—", role: "—" }}
                  />
                </div>
              </div>
            </section>
          ))}

          <p className="text-base03 text-xs border-t border-base03 pt-4">
            To switch themes: update <code>ACTIVE_THEME</code> in <code>lib/active-theme.ts</code>
          </p>
        </main>
      </div>
    </div>
  );
}
