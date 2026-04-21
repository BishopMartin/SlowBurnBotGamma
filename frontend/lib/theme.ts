/**
 * Semantic status colors — mirrors `:root` in `app/globals.css`.
 * In UI, prefer Tailwind: `text-status-ok` (nav active + on/success), `text-status-bad`, `hover:text-status-bad-hover`.
 * Update both files when changing the palette.
 */
export const statusColors = {
  ok: "#adcc00",
  bad: "#cf3b0a",
  badHover: "#e87755",
} as const;
