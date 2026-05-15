import type { Metadata } from "next";
import Link from "next/link";
import { Bracket } from "@/lib/bracket";
import { loadTheme } from "@/lib/theme-loader";

export const metadata: Metadata = {
  title: "Colors — SlowBurnBot",
  description: "Frontend color palette reference",
};

// Site-specific descriptions for the slots that map to real website usage.
// Slots absent from this lookup show "—" / "reserved" in the table.
const SITE_INFO: Record<string, { name: string; role: string; description: string }> = {
  base00: { name: "charcoal bg",       role: "Page background (`--background`), selected option text on `<select>`", description: "Near-black charcoal with a warm brown cast" },
  base01: { name: "header bar",        role: "Section headers, table header strips",                                   description: "Slightly lifted warm dark panel" },
  base02: { name: "panel brown-gray",  role: "`<select>` option background, row hovers, panels",                      description: "Dark warm gray-brown" },
  base03: { name: "border taupe",      role: "Borders, dividers, breadcrumbs, empty cells",                           description: "Muted taupe line color" },
  base04: { name: "muted taupe text",  role: "Secondary / meta text across the UI",                                   description: "Gray-taupe secondary text" },
  base05: { name: "ivory text",        role: "Primary text (`--foreground`), autofill text",                          description: "Warm off-white / light ivory" },
  base07: { name: "pure white hover",  role: "Nav/tab hover (`text-white` variants)",                                  description: "Pure white" },
  base08: { name: "ember red",         role: "Error / destructive (`--status-bad`, `text-status-bad`)",               description: "Orange-red" },
  base09: { name: "terracotta accent", role: "Links, CTAs, focus rings, `<select>` accent",                           description: "Burnt orange / terracotta" },
  base0A: { name: "wheat highlight",   role: "Counts, tokens, warm highlights (e.g. Clients)",                        description: "Wheat / pale gold" },
  base0B: { name: "chartreuse ok",     role: "Success / on (`--status-ok`, `text-status-ok`)",                        description: "Bright yellow-green / chartreuse" },
  base11: { name: "dropdown hover",    role: "Dropdown row hover (`dropdown.tsx`)",                                    description: "Mid warm gray-brown" },
  base12: { name: "coral hover",       role: "Bad control hover (`--status-bad-hover`)",                              description: "Salmon / coral-orange" },
};

const SECTIONS: Array<{ label: string; slots: string[] }> = [
  { label: "MONOTONES",  slots: ["base00", "base01", "base02", "base03", "base04", "base05", "base06", "base07"] },
  { label: "ACCENTS",    slots: ["base08", "base09", "base0A", "base0B", "base0C", "base0D", "base0E", "base0F"] },
  { label: "EXTENSIONS", slots: ["base10", "base11"] },
  { label: "BRIGHTS",    slots: ["base12", "base13", "base14", "base15", "base16", "base17"] },
];

export default function ColorsPage() {
  const { palette } = loadTheme("slowburnbot");

  return (
    <div className="min-h-screen flex flex-col font-mono text-sm">
      <div className="flex-1 max-w-6xl mx-auto w-full sm:border-x border-[#3d3d3a]">
        <header className="px-3 sm:px-6 py-3 flex flex-wrap items-baseline gap-x-4 gap-y-2 border-b border-[#3d3d3a]">
          <span className="font-semibold text-[#d97757]">SlowBurnBot</span>
          <span className="text-[#9a968b]">colors</span>
          <span className="text-[#3d3d3a] hidden sm:inline">—</span>
          <Link href="/login" className="text-[#9a968b] hover:text-[#d97757] transition-colors">
            <Bracket className="">sign in</Bracket>
          </Link>
          <Link href="/dashboard" className="text-[#9a968b] hover:text-[#d97757] transition-colors">
            <Bracket className="">dashboard</Bracket>
          </Link>
        </header>

        <main className="px-3 sm:px-6 py-6 space-y-6">
          <p className="text-[#9a968b]">
            Frontend palette reference — colors loaded from{" "}
            <code className="text-[#e5c07b]">themes/slowburnbot.yaml</code>.
            Replace the file to change the entire theme without touching code.
          </p>

          {SECTIONS.map(({ label, slots }) => (
            <section key={label}>
              <h2 className="text-[#9a968b] mb-2">{label}</h2>
              <div className="border border-[#3d3d3a] overflow-x-auto">
                <table className="w-full min-w-[720px] text-left border-collapse">
                  <thead>
                    <tr className="text-[#9a968b] border-b border-[#3d3d3a] bg-[#1a1918]">
                      <th className="px-3 py-2 font-normal whitespace-nowrap">Slot</th>
                      <th className="px-2 py-2 font-normal w-20">Sample</th>
                      <th className="px-3 py-2 font-normal whitespace-nowrap">Hex</th>
                      <th className="px-3 py-2 font-normal">Name</th>
                      <th className="px-3 py-2 font-normal min-w-[12rem]">Role</th>
                      <th className="px-3 py-2 font-normal min-w-[10rem]">Description</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#3d3d3a]">
                    {slots.map((slotId) => {
                      const rawHex = palette[slotId] ?? "";
                      const hex = `#${rawHex.replace(/^#/, "")}`;
                      const info = SITE_INFO[slotId];
                      return (
                        <tr key={slotId} className="hover:bg-[#1f1e1d] transition-colors align-top">
                          <td className="px-3 py-3 text-[#f4f3ee] whitespace-nowrap">{slotId}</td>
                          <td className="px-2 py-2 w-20">
                            <div
                              className="min-h-10 min-w-14 rounded-sm border border-[#3d3d3a] shadow-inner shrink-0"
                              style={{ backgroundColor: hex }}
                              role="img"
                              aria-label={`Swatch ${slotId}`}
                              title={hex}
                            />
                          </td>
                          <td className="px-3 py-3 text-[#e5c07b] whitespace-nowrap">{hex}</td>
                          <td className="px-3 py-3 text-[#f4f3ee]">{info?.name ?? "—"}</td>
                          <td className="px-3 py-3 text-[#9a968b]">{info?.role ?? "reserved"}</td>
                          <td className="px-3 py-3 text-[#9a968b]">{info?.description ?? "—"}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          ))}

          <p className="text-[#9a968b] text-xs border-t border-[#3d3d3a] pt-4">
            Note: <code className="text-[#e5c07b]">#5a5850</code> (disabled gray — system-disabled rows, muted{" "}
            affordances) is used in the codebase but has no base24 slot assignment. It will be mapped to the nearest
            slot in Phase 2.
          </p>
        </main>
      </div>
    </div>
  );
}
