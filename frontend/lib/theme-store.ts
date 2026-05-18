const KEY = "sbb-theme";

export function getStoredTheme(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(KEY);
}

export function setStoredTheme(slug: string): void {
  localStorage.setItem(KEY, slug);
}

export function clearStoredTheme(): void {
  localStorage.removeItem(KEY);
}

export function applyThemeCss(css: string): void {
  const pairs = css.split(";").filter(Boolean);
  for (const pair of pairs) {
    const idx = pair.indexOf(":");
    if (idx === -1) continue;
    const prop = pair.slice(0, idx).trim();
    const val  = pair.slice(idx + 1).trim();
    document.documentElement.style.setProperty(prop, val);
  }
}
