"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { logout } from "@/lib/api";
import { Bracket } from "@/lib/bracket";
import { APP_VERSION } from "@/lib/version";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [user, loading, router]);

  if (loading || !user) {
    return <div className="min-h-screen flex items-center justify-center font-mono text-[#73726c]">loading…</div>;
  }

  async function handleLogout() {
    await logout();
    router.push("/login");
  }

  const navItems = [
    { href: "/dashboard", label: "overview" },
    { href: "/dashboard/accounts", label: "accounts" },
    { href: "/dashboard/logs", label: "logs" },
    ...(user.is_superuser ? [{ href: "/admin", label: "admin" }] : []),
  ];

  return (
    <div className="min-h-screen flex flex-col font-mono">
      <header className="border-b border-[#3d3d3a] px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <span className="font-semibold text-[#d97757]">SlowBurnBot</span>
          <nav className="flex gap-4">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`transition-colors ${
                  pathname === item.href
                    ? "text-[#f0eee6]"
                    : "text-[#73726c] hover:text-[#f0eee6]"
                }`}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-[#3d3d3a]">v{APP_VERSION}</span>
          <span className="text-[#73726c]">{user.email}</span>
          <button onClick={handleLogout} className="group transition-colors">
            <Bracket className="text-[#73726c] group-hover:text-[#d97757]">sign out</Bracket>
          </button>
        </div>
      </header>
      <main className="flex-1 p-6 max-w-5xl mx-auto w-full">{children}</main>
    </div>
  );
}
