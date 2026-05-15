import type { Metadata } from "next";
import { Fragment } from "react";
import Link from "next/link";
import { Bracket } from "@/lib/bracket";
import { loadTheme } from "@/lib/theme-loader";
import { ACTIVE_THEME } from "@/lib/active-theme";

export const metadata: Metadata = {
  title: "Colors — SlowBurnBot",
  description: "Frontend color palette reference",
};

const SITE_INFO: Record<string, { name: string; role: string }> = {
  base00: { name: "charcoal bg",    role: "Page background  —  --background" },
  base01: { name: "header bar",     role: "Section headers, table strips" },
  base02: { name: "panel",          role: "Select option bg, row hovers, panels" },
  base03: { name: "border taupe",   role: "Borders, dividers, disabled text" },
  base04: { name: "muted text",     role: "Secondary / meta text" },
  base05: { name: "ivory text",     role: "Primary text  —  --foreground" },
  base06: { name: "—",              role: "reserved" },
  base07: { name: "white",          role: "Nav/tab hover" },
  base08: { name: "ember red",      role: "Error / destructive  —  --status-bad" },
  base09: { name: "terracotta",     role: "Links, CTAs, focus rings, accent" },
  base0A: { name: "wheat",          role: "Counts, tokens, warm highlights" },
  base0B: { name: "chartreuse",     role: "Success  —  --status-ok" },
  base0C: { name: "—",              role: "reserved" },
  base0D: { name: "—",              role: "reserved" },
  base0E: { name: "—",              role: "reserved" },
  base0F: { name: "—",              role: "reserved" },
  base10: { name: "—",              role: "reserved" },
  base11: { name: "dropdown hover", role: "Dropdown row hover" },
  base12: { name: "coral hover",    role: "Bad control hover  —  --status-bad-hover" },
  base13: { name: "—",              role: "reserved" },
  base14: { name: "—",              role: "reserved" },
  base15: { name: "—",              role: "reserved" },
  base16: { name: "—",              role: "reserved" },
  base17: { name: "—",              role: "reserved" },
};

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
  base09: { name: "Orange",               role: "Integers, booleans, constants, attributes" },
  base0A: { name: "Yellow",               role: "Classes, bold, search text background" },
  base0B: { name: "Green",                role: "Strings, inherited class, diff inserted" },
  base0C: { name: "Cyan",                 role: "Support, regex, escape characters" },
  base0D: { name: "Blue",                 role: "Functions, methods, headings" },
  base0E: { name: "Purple",               role: "Keywords, storage, selector, italic" },
  base0F: { name: "Brown",                role: "Deprecated, embedded language tags" },
  base10: { name: "Darker Background",    role: "Darker background" },
  base11: { name: "Brighter Background",  role: "Brighter background" },
  base12: { name: "Bright Red",           role: "Bright red" },
  base13: { name: "Bright Yellow",        role: "Bright yellow / orange" },
  base14: { name: "Bright Green",         role: "Bright green" },
  base15: { name: "Bright Cyan",          role: "Bright cyan" },
  base16: { name: "Bright Blue",          role: "Bright blue" },
  base17: { name: "Bright Purple",        role: "Bright purple / magenta" },
};

const SECTIONS: Array<{ label: string; slots: string[] }> = [
  { label: "MONOTONES",  slots: ["base00","base01","base02","base03","base04","base05","base06","base07"] },
  { label: "ACCENTS",    slots: ["base08","base09","base0A","base0B","base0C","base0D","base0E","base0F"] },
  { label: "EXTENSIONS", slots: ["base10","base11"] },
  { label: "BRIGHTS",    slots: ["base12","base13","base14","base15","base16","base17"] },
];

type Pal = Record<string, string>;

function ph(p: Pal, slot: string): string {
  return `#${p[slot]?.replace(/^#/, "") ?? "000000"}`;
}

// 9-column grid: [4 left] [gap] [4 right]
// Both sides share the same grid rows — heights always match.
const COLS = "5.5rem 8.5rem 10rem 1fr 14px 5.5rem 8.5rem 10rem 1fr";

const FS_MAIN  = "0.9rem";
const FS_MUTED = "0.82rem";
const FS_LABEL = "0.75rem";
const PAD      = "7px 12px";

function border(p: Pal, last: boolean) {
  return last ? "none" : `1px solid ${ph(p, "base03")}`;
}

// Spacer column — just fills the gap between panels
function Gap({ last, lp, rp }: { last?: boolean; lp: Pal; rp: Pal }) {
  // Use a gradient so the gap visually separates the two backgrounds
  return (
    <div style={{
      borderBottom: last ? "none" : `1px solid transparent`,
      background: "transparent",
    }} />
  );
}

// Theme name banner — spans all 4 of its half's columns
function Banner({ p, name, right }: { p: Pal; name: string; right?: boolean }) {
  return (
    <div style={{
      gridColumn: right ? "6 / 10" : "1 / 5",
      backgroundColor: ph(p, "base01"),
      borderBottom: `1px solid ${ph(p, "base03")}`,
      borderLeft:  right ? `1px solid ${ph(p, "base03")}` : `1px solid ${ph(p, "base03")}`,
      borderRight: `1px solid ${ph(p, "base03")}`,
      borderTop:   `1px solid ${ph(p, "base03")}`,
      padding: "7px 12px",
      color: ph(p, "base09"),
      fontWeight: 600,
      fontSize: FS_MAIN,
    }}>
      {name}
    </div>
  );
}

// Column label cells (slot / hex / name / role)
function ColLabel({ p, label, first, last4, right }: { p: Pal; label: string; first?: boolean; last4?: boolean; right?: boolean }) {
  return (
    <div style={{
      backgroundColor: ph(p, "base01"),
      borderBottom: `1px solid ${ph(p, "base03")}`,
      borderLeft:  first ? `1px solid ${ph(p, "base03")}` : undefined,
      borderRight: last4 ? `1px solid ${ph(p, "base03")}` : undefined,
      padding: "4px 12px",
      color: ph(p, "base03"),
      fontSize: FS_LABEL,
    }}>
      {label}
    </div>
  );
}

// Slot ID cell
function SlotCell({ p, slotId, last, first }: { p: Pal; slotId: string; last: boolean; first?: boolean }) {
  return (
    <div style={{
      backgroundColor: ph(p, "base00"),
      borderBottom: border(p, last),
      borderLeft: `1px solid ${ph(p, "base03")}`,
      padding: PAD,
      color: ph(p, "base05"),
      fontSize: FS_MAIN,
      alignSelf: "stretch",
    }}>
      {slotId}
    </div>
  );
}

// Swatch + hex cell — swatch top-aligned
function HexCell({ p, slotId, last }: { p: Pal; slotId: string; last: boolean }) {
  const slotHex = ph(p, slotId);
  return (
    <div style={{
      backgroundColor: ph(p, "base00"),
      borderBottom: border(p, last),
      padding: PAD,
      display: "flex",
      alignItems: "flex-start",
      gap: "7px",
    }}>
      <div style={{
        width: "17px",
        height: "17px",
        backgroundColor: slotHex,
        border: `1px solid ${ph(p, "base03")}`,
        borderRadius: "2px",
        flexShrink: 0,
        marginTop: "1px",
      }} />
      <span style={{ color: ph(p, "base04"), fontSize: FS_MUTED }}>{slotHex}</span>
    </div>
  );
}

// Name cell (primary text)
function NameCell({ p, value, last }: { p: Pal; value: string; last: boolean }) {
  return (
    <div style={{
      backgroundColor: ph(p, "base00"),
      borderBottom: border(p, last),
      padding: PAD,
      color: ph(p, "base05"),
      fontSize: FS_MAIN,
    }}>
      {value}
    </div>
  );
}

// Role cell (muted text) + optional right border
function RoleCell({ p, value, last, rightBorder }: { p: Pal; value: string; last: boolean; rightBorder?: boolean }) {
  return (
    <div style={{
      backgroundColor: ph(p, "base00"),
      borderBottom: border(p, last),
      borderRight: rightBorder ? `1px solid ${ph(p, "base03")}` : undefined,
      padding: PAD,
      color: ph(p, "base04"),
      fontSize: FS_MUTED,
    }}>
      {value}
    </div>
  );
}

export default function ColorsPage() {
  const def = loadTheme("slowburnbot");
  const act = loadTheme(ACTIVE_THEME);

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
            Active: <code className="text-base0a">{ACTIVE_THEME}</code>
            <span className="text-base03 mx-2">/</span>
            Default: <code className="text-base04">slowburnbot</code>
          </p>

          {SECTIONS.map(({ label, slots }) => (
            <section key={label}>
              <h2 className="text-base04 mb-2 text-xs tracking-widest">{label}</h2>
              <div className="overflow-x-auto">
                {/* Single 9-col grid — both panels share rows, heights always match */}
                <div style={{ display: "grid", gridTemplateColumns: COLS, minWidth: "900px" }}>

                  {/* Banner row: theme names spanning 4 cols each */}
                  <Banner p={def.palette} name={def.name} />
                  <Gap lp={def.palette} rp={act.palette} />
                  <Banner p={act.palette} name={act.name} right />

                  {/* Column label row */}
                  <ColLabel p={def.palette} label="slot"  first />
                  <ColLabel p={def.palette} label="hex"   />
                  <ColLabel p={def.palette} label="name"  />
                  <ColLabel p={def.palette} label="role"  />
                  <Gap lp={def.palette} rp={act.palette} />
                  <ColLabel p={act.palette} label="slot"  first />
                  <ColLabel p={act.palette} label="hex"   />
                  <ColLabel p={act.palette} label="name"  />
                  <ColLabel p={act.palette} label="role"  last4 right />

                  {/* Data rows — one row per slot, both sides in the same grid row */}
                  {slots.map((slotId, i) => {
                    const last  = i === slots.length - 1;
                    const linfo = SITE_INFO[slotId]   ?? { name: "—", role: "reserved" };
                    const rinfo = BASE24_SPEC[slotId]  ?? { name: "—", role: "—" };
                    return (
                      <Fragment key={slotId}>
                        <SlotCell p={def.palette} slotId={slotId} last={last} />
                        <HexCell  p={def.palette} slotId={slotId} last={last} />
                        <NameCell p={def.palette} value={linfo.name} last={last} />
                        <RoleCell p={def.palette} value={linfo.role} last={last} />
                        <Gap lp={def.palette} rp={act.palette} last={last} />
                        <SlotCell p={act.palette} slotId={slotId} last={last} />
                        <HexCell  p={act.palette} slotId={slotId} last={last} />
                        <NameCell p={act.palette} value={rinfo.name} last={last} />
                        <RoleCell p={act.palette} value={rinfo.role} last={last} rightBorder />
                      </Fragment>
                    );
                  })}

                </div>
              </div>
            </section>
          ))}

          <p className="text-base03 text-xs border-t border-base03 pt-4">
            Change theme: edit <code>ACTIVE_THEME</code> in <code>lib/active-theme.ts</code>
          </p>
        </main>
      </div>
    </div>
  );
}
