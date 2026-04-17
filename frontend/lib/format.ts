/**
 * Format a time string (e.g. "09:00", "21:30:00") as "09:00 AM" / "09:30 PM"
 */
export function formatTime(t: string | null | undefined): string {
  if (!t) return "?";
  const [h, m] = t.split(":").map(Number);
  const period = h >= 12 ? "PM" : "AM";
  const hour12 = h % 12 || 12;
  return `${String(hour12).padStart(2, "0")}:${String(m).padStart(2, "0")} ${period}`;
}

/**
 * Build a readable schedule label from AccountSettings fields.
 */
export function scheduleLabel(s: {
  schedule_days?: string | null;
  schedule_start?: string | null;
  schedule_end?: string | null;
  max_runs_per_day?: number | null;
} | undefined): string {
  if (!s) return "—";
  const parts: string[] = [];
  if (s.schedule_days) parts.push(s.schedule_days);
  if (s.schedule_start || s.schedule_end) {
    parts.push(`${formatTime(s.schedule_start)} - ${formatTime(s.schedule_end)}`);
  }
  if (s.max_runs_per_day && s.max_runs_per_day > 1) parts.push(`x${s.max_runs_per_day}/day`);
  return parts.length ? parts.join("  ") : "—";
}
