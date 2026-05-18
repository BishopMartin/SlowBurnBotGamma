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
  base08: { name: "coral hover",     role: "Bad control hover  —  --status-bad-hover" },
  base09: { name: "terracotta",     role: "Links, CTAs, focus rings, accent" },
  base0A: { name: "wheat",          role: "Counts, tokens, warm highlights" },
  base0B: { name: "chartreuse",     role: "Success  —  --status-ok" },
  base0C: { name: "—",              role: "reserved" },
  base0D: { name: "—",              role: "reserved" },
  base0E: { name: "—",              role: "reserved" },
  base0F: { name: "—",              role: "reserved" },
  base10: { name: "—",              role: "reserved" },
  base11: { name: "dropdown hover", role: "Dropdown row hover" },
  base12: { name: "ember red",       role: "Error / destructive  —  --status-bad" },
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

// 9-col grid: [slot+hex | swatch | name | role] [gap] [slot+hex | swatch | name | role]
const COLS = "6.5rem 3.2rem 18rem 1fr 10px 6.5rem 3.2rem 18rem 1fr";

const FS = "0.95rem";
const PAD = "7px 10px";

function border(p: Pal, last: boolean) {
  return last ? "none" : `1px solid ${ph(p, "base03")}`;
}

// Pure black spacer — no theme color bleeds through the gap
function Gap({ last }: { last?: boolean }) {
  return <div style={{ background: "#000" }} />;
}

// Theme name banner — spans all 4 of its half's columns
function Banner({ p, name, right }: { p: Pal; name: string; right?: boolean }) {
  return (
    <div style={{
      gridColumn: right ? "6 / 10" : "1 / 5",
      backgroundColor: ph(p, "base01"),
      borderBottom: `1px solid ${ph(p, "base03")}`,
      borderLeft:   `1px solid ${ph(p, "base03")}`,
      borderRight:  `1px solid ${ph(p, "base03")}`,
      borderTop:    `1px solid ${ph(p, "base03")}`,
      padding: PAD,
      color: ph(p, "base09"),
      fontWeight: 600,
      fontSize: FS,
    }}>
      {name}
    </div>
  );
}

// Column label cells (slot / hex / name / role)
function ColLabel({ p, label, first, last4 }: { p: Pal; label: string; first?: boolean; last4?: boolean }) {
  return (
    <div style={{
      backgroundColor: ph(p, "base01"),
      borderBottom: `1px solid ${ph(p, "base03")}`,
      borderLeft:  first ? `1px solid ${ph(p, "base03")}` : undefined,
      borderRight: last4 ? `1px solid ${ph(p, "base03")}` : undefined,
      padding: "5px 11px",
      color: ph(p, "base03"),
      fontSize: FS,
    }}>
      {label}
    </div>
  );
}

// Slot + hex stacked in one cell
function SlotHexCell({ p, slotId, last }: { p: Pal; slotId: string; last: boolean }) {
  return (
    <div style={{
      backgroundColor: ph(p, "base00"),
      borderBottom: border(p, last),
      borderLeft: `1px solid ${ph(p, "base03")}`,
      padding: PAD,
      display: "flex",
      flexDirection: "column",
      gap: "3px",
      alignSelf: "stretch",
    }}>
      <span style={{ color: ph(p, "base05"), fontSize: FS }}>{slotId}</span>
      <span style={{ color: ph(p, "base04"), fontSize: FS }}>{ph(p, slotId)}</span>
    </div>
  );
}

// Swatch-only cell — larger square
function SwatchCell({ p, slotId, last }: { p: Pal; slotId: string; last: boolean }) {
  return (
    <div style={{
      backgroundColor: ph(p, "base00"),
      borderBottom: border(p, last),
      padding: "8px 6px",
      display: "flex",
      alignItems: "flex-start",
      justifyContent: "center",
    }}>
      <div style={{
        width: "38px",
        height: "38px",
        backgroundColor: ph(p, slotId),
        border: `1px solid ${ph(p, "base03")}`,
        borderRadius: "3px",
        flexShrink: 0,
      }} />
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
      fontSize: FS,
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
      fontSize: FS,
    }}>
      {value}
    </div>
  );
}

export default function ColorsPage() {
  const def = loadTheme("slowburnbot");
  const act = loadTheme(ACTIVE_THEME);

  return (
    // Entire page is black — no theme var bleeds into the chrome or gaps
    <div style={{ background: "#000", minHeight: "100vh", fontFamily: "monospace" }}>
      <div style={{ maxWidth: "1600px", margin: "0 auto", padding: "0 16px" }}>

        <header style={{
          padding: "10px 0",
          display: "flex",
          flexWrap: "nowrap",
          alignItems: "baseline",
          gap: "6px 14px",
          borderBottom: `1px solid ${ph(def.palette, "base03")}`,
          marginBottom: "24px",
        }}>
          <span style={{ fontWeight: 600, color: ph(def.palette, "base09"), fontSize: "1rem" }}>SlowBurnBot</span>
          <span style={{ color: ph(def.palette, "base04"), fontSize: "1rem" }}>colors</span>
          <span style={{ color: ph(def.palette, "base03") }}>—</span>
          <Link href="/login" style={{ color: ph(def.palette, "base04"), textDecoration: "none", fontSize: "1rem" }}>
            <Bracket className="">sign in</Bracket>
          </Link>
          <Link href="/dashboard" style={{ color: ph(def.palette, "base04"), textDecoration: "none", fontSize: "1rem" }}>
            <Bracket className="">dashboard</Bracket>
          </Link>
        </header>

        <div style={{ marginBottom: "16px", fontSize: "0.9rem" }}>
          <span style={{ color: ph(def.palette, "base04") }}>Active: </span>
          <code style={{ color: ph(def.palette, "base0A") }}>{ACTIVE_THEME}</code>
          <span style={{ color: ph(def.palette, "base03"), margin: "0 8px" }}>/</span>
          <span style={{ color: ph(def.palette, "base04") }}>Default: </span>
          <code style={{ color: ph(def.palette, "base04") }}>slowburnbot</code>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "32px" }}>
          {SECTIONS.map(({ label, slots }) => (
            <section key={label}>
              <div style={{ color: ph(def.palette, "base04"), marginBottom: "8px", fontSize: "0.75rem", letterSpacing: "0.1em" }}>
                {label}
              </div>
              <div style={{ overflowX: "auto" }}>
                <div style={{ display: "grid", gridTemplateColumns: COLS, minWidth: "860px" }}>

                  {/* Banner row */}
                  <Banner p={def.palette} name={def.name} />
                  <Gap />
                  <Banner p={act.palette} name={act.name} right />

                  {/* Column label row */}
                  <ColLabel p={def.palette} label="slot/hex" first />
                  <ColLabel p={def.palette} label=""            />
                  <ColLabel p={def.palette} label="name"        />
                  <ColLabel p={def.palette} label="role"        />
                  <Gap />
                  <ColLabel p={act.palette} label="slot/hex" first />
                  <ColLabel p={act.palette} label=""            />
                  <ColLabel p={act.palette} label="name"        />
                  <ColLabel p={act.palette} label="role"        last4 />

                  {/* Data rows */}
                  {slots.map((slotId, i) => {
                    const last  = i === slots.length - 1;
                    const linfo = SITE_INFO[slotId]  ?? { name: "—", role: "reserved" };
                    const rinfo = BASE24_SPEC[slotId] ?? { name: "—", role: "—" };
                    return (
                      <Fragment key={slotId}>
                        <SlotHexCell p={def.palette} slotId={slotId} last={last} />
                        <SwatchCell  p={def.palette} slotId={slotId} last={last} />
                        <NameCell    p={def.palette} value={linfo.name} last={last} />
                        <RoleCell    p={def.palette} value={linfo.role} last={last} />
                        <Gap last={last} />
                        <SlotHexCell p={act.palette} slotId={slotId} last={last} />
                        <SwatchCell  p={act.palette} slotId={slotId} last={last} />
                        <NameCell    p={act.palette} value={rinfo.name} last={last} />
                        <RoleCell    p={act.palette} value={rinfo.role} last={last} rightBorder />
                      </Fragment>
                    );
                  })}

                </div>
              </div>
            </section>
          ))}
        </div>

        <footer style={{ color: ph(def.palette, "base03"), fontSize: "0.75rem", borderTop: `1px solid ${ph(def.palette, "base03")}`, padding: "16px 0", marginTop: "32px" }}>
          Change theme: edit <code>ACTIVE_THEME</code> in <code>lib/active-theme.ts</code>
        </footer>

      </div>
    </div>
  );
}
