import type { Metadata } from "next";
import Link from "next/link";
import { Bracket } from "@/lib/bracket";

export const metadata: Metadata = {
  title: "Colors — SlowBurnBot",
  description: "Frontend color palette reference",
};

const ROWS: ReadonlyArray<{
  group: string;
  hex: string;
  name: string;
  role: string;
  description: string;
}> = [
  {
    group: "GLOBAL / CSS",
    hex: "#141413",
    name: "charcoal bg",
    role:
      "Page background (`--background`), selected option text on `<select>`",
    description: "Near-black charcoal with a warm brown cast",
  },
  {
    group: "GLOBAL / CSS",
    hex: "#f4f3ee",
    name: "ivory text",
    role: "Primary text (`--foreground`), autofill text",
    description: "Warm off-white / light ivory",
  },
  {
    group: "GLOBAL / CSS",
    hex: "#adcc00",
    name: "chartreuse ok",
    role: "Success / on (`--status-ok`, `text-status-ok`)",
    description: "Bright yellow-green / chartreuse",
  },
  {
    group: "GLOBAL / CSS",
    hex: "#cf3b0a",
    name: "ember red",
    role: "Error / destructive (`--status-bad`, `text-status-bad`)",
    description: "Orange-red",
  },
  {
    group: "GLOBAL / CSS",
    hex: "#e87755",
    name: "coral hover",
    role: "Bad control hover (`--status-bad-hover`)",
    description: "Salmon / coral-orange",
  },
  {
    group: "GLOBAL / CSS",
    hex: "#d97757",
    name: "terracotta accent",
    role: "Links, CTAs, focus rings, `<select>` accent",
    description: "Burnt orange / terracotta",
  },
  {
    group: "GLOBAL / CSS",
    hex: "#1f1e1d",
    name: "panel brown-gray",
    role: "`<select>` option background, row hovers, panels",
    description: "Dark warm gray-brown",
  },
  {
    group: "COMPONENTS",
    hex: "#1a1918",
    name: "header bar",
    role: "Section headers, table header strips",
    description: "Slightly lifted warm dark panel",
  },
  {
    group: "COMPONENTS",
    hex: "#2a2927",
    name: "dropdown hover",
    role: "Dropdown row hover (`dropdown.tsx`)",
    description: "Mid warm gray-brown",
  },
  {
    group: "COMPONENTS",
    hex: "#3d3d3a",
    name: "border taupe",
    role: "Borders, dividers, breadcrumbs, empty cells",
    description: "Muted taupe line color",
  },
  {
    group: "COMPONENTS",
    hex: "#5a5850",
    name: "disabled gray",
    role: 'System-disabled rows, muted "-" affordances',
    description: "Dusty mid gray",
  },
  {
    group: "COMPONENTS",
    hex: "#9a968b",
    name: "muted taupe text",
    role: "Secondary / meta text across the UI",
    description: "Gray-taupe secondary text",
  },
  {
    group: "COMPONENTS",
    hex: "#e5c07b",
    name: "wheat highlight",
    role: "Counts, tokens, warm highlights (e.g. Clients)",
    description: "Wheat / pale gold",
  },
  {
    group: "COMPONENTS",
    hex: "#ffffff",
    name: "pure white hover",
    role: "Nav/tab hover (`text-white` variants)",
    description: "Pure white",
  },
];

export default function ColorsPage() {
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

        <main className="px-3 sm:px-6 py-6">
          <p className="text-[#9a968b] mb-4">
            Frontend palette reference — same hex values used in Tailwind arbitrary classes and{" "}
            <code className="text-[#e5c07b]">globals.css</code>.
          </p>

          <div className="border border-[#3d3d3a] overflow-x-auto">
            <table className="w-full min-w-[720px] text-left border-collapse">
              <thead>
                <tr className="text-[#9a968b] border-b border-[#3d3d3a] bg-[#1a1918]">
                  <th className="px-3 py-2 font-normal whitespace-nowrap">Group</th>
                  <th className="px-2 py-2 font-normal w-20">Sample</th>
                  <th className="px-3 py-2 font-normal whitespace-nowrap">Hex</th>
                  <th className="px-3 py-2 font-normal">Name</th>
                  <th className="px-3 py-2 font-normal min-w-[12rem]">Role</th>
                  <th className="px-3 py-2 font-normal min-w-[10rem]">Description</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#3d3d3a]">
                {ROWS.map((row) => (
                  <tr key={row.hex + row.group} className="hover:bg-[#1f1e1d] transition-colors align-top">
                    <td className="px-3 py-3 text-[#9a968b] whitespace-nowrap">{row.group}</td>
                    <td className="px-2 py-2 w-20">
                      <div
                        className="min-h-10 min-w-14 rounded-sm border border-[#3d3d3a] shadow-inner shrink-0"
                        style={{ backgroundColor: row.hex }}
                        role="img"
                        aria-label={`Swatch ${row.hex}`}
                        title={row.hex}
                      />
                    </td>
                    <td className="px-3 py-3 text-[#e5c07b] whitespace-nowrap">{row.hex}</td>
                    <td className="px-3 py-3 text-[#f4f3ee]">{row.name}</td>
                    <td className="px-3 py-3 text-[#9a968b]">{row.role}</td>
                    <td className="px-3 py-3 text-[#9a968b]">{row.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </main>
      </div>
    </div>
  );
}
