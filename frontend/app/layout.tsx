import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";
import { loadTheme } from "@/lib/theme-loader";

export const metadata: Metadata = {
  title: "SlowBurnBot",
  description: "Bot management dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const theme = loadTheme("tokyo-night-storm");

  return (
    <html lang="en">
      <head>
        <style
          // Inject the base24 palette before paint.
          // Source: frontend/themes/slowburnbot.yaml
          dangerouslySetInnerHTML={{ __html: `:root{${theme.css}}` }}
        />
      </head>
      <body className="min-h-screen">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
