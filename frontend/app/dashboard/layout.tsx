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
    return <div className="min-h-screen flex items-center justify-center font-mono text-[#B1ADA1]">loading…</div>;
  }

  async function handleLogout() {
    await logout();
    router.push("/login");
  }

  const navItems = [
    { href: "/dashboard", label: "overview" },
    { href: "/dashboard/accounts", label: "accounts" },
    { href: "/dashboard/config", label: "config" },
    ...(user.is_superuser ? [{ href: "/admin", label: "admin" }] : []),
  ];

  function isNavActive(href: string) {
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname === href || pathname.startsWith(`${href}/`);
  }

  return (
    <div className="min-h-screen flex flex-col font-mono">
      <div className="flex-1 max-w-5xl mx-auto w-full border-x border-[#3d3d3a]">
        <header className="px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <span className="font-semibold text-[#d97757]">SlowBurnBot</span>
            <span className="text-[#3d3d3a]">--</span>
            <nav className="flex gap-1">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`transition-colors ${
                    isNavActive(item.href)
                      ? "text-[#d97757]"
                      : "text-[#B1ADA1] hover:text-white"
                  }`}
                >
                  <span className="text-[#f4f3ee]">[</span>{item.label}<span className="text-[#f4f3ee]">]</span>
                </Link>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-4">
            <button onClick={() => window.location.reload()} className="text-[#3d3d3a] hover:text-[#B1ADA1] cursor-pointer transition-colors" title="Click to reload">v{APP_VERSION}</button>
            <span className="text-[#eab308]">{user.email}</span>
            <button onClick={handleLogout} className="group transition-colors">
              <Bracket className="text-[#B1ADA1] group-hover:text-[#d97757]">sign out</Bracket>
            </button>
          </div>
        </header>
        <main className="px-6 py-6">{children}</main>
      </div>
    </div>
  );
}
