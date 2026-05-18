"use client";

import { useEffect } from "react";
import { getStoredTheme, applyThemeCss } from "./theme-store";

export function ThemeProvider() {
  useEffect(() => {
    const slug = getStoredTheme();
    if (!slug) return;
    fetch(`/api/themes/${encodeURIComponent(slug)}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => { if (data?.css) applyThemeCss(data.css); })
      .catch(() => {});
  }, []);

  return null;
}
