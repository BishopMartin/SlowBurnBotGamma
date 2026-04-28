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
    return <div className="min-h-screen flex items-center justify-center font-mono text-[#9A968B]">loading…</div>;
  }

  async function handleLogout() {
    await logout();
    router.push("/login");
  }

  const navItems = [
    { href: "/dashboard", label: "overview" },
    { href: "/dashboard/accounts", label: "accounts" },
    { href: "/dashboard/clients", label: "clients" },
    { href: "/dashboard/config", label: "config" },
    ...(user.is_superuser ? [{ href: "/admin", label: "admin" }] : []),
  ];

  function isNavActive(href: string) {
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname === href || pathname.startsWith(`${href}/`);
  }

  return (
    <div className="min-h-screen flex flex-col font-mono">
      <div className="flex-1 max-w-5xl mx-auto w-full sm:border-x border-[#3d3d3a]">
        <header className="px-3 sm:px-6 pt-2 pb-3 flex flex-wrap items-center gap-x-2 gap-y-1">
          <span className="font-semibold text-[#d97757]">SlowBurnBot <span className="text-[#3d3d3a] font-normal">--</span></span>
          <nav className="flex flex-wrap gap-1">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`transition-colors ${
                  isNavActive(item.href)
                    ? "text-[#d97757]"
                    : "text-[#9A968B] hover:text-white"
                }`}
              >
                <span className="text-[#f4f3ee]">[</span>{item.label}<span className="text-[#f4f3ee]">]</span>
              </Link>
            ))}
          </nav>
          <div className="flex items-center gap-3 sm:gap-4 ml-auto">
            <button onClick={() => window.location.reload()} className="text-[#3d3d3a] hover:text-[#9A968B] cursor-pointer transition-colors" title="Click to reload">v{APP_VERSION}</button>
            <span className="text-[#E5C07B] truncate max-w-[12rem] sm:max-w-none">{user.email}</span>
            <div className="flex gap-1">
              <Link href="/dashboard/plan" className={`group transition-colors ${pathname.startsWith("/dashboard/plan") ? "text-[#d97757]" : ""}`}>
                <Bracket className="text-[#9A968B] group-hover:text-[#d97757]">plan</Bracket>
              </Link>
              <button onClick={handleLogout} className="group transition-colors">
                <Bracket className="text-[#9A968B] group-hover:text-[#d97757]">log out</Bracket>
              </button>
            </div>
          </div>
        </header>
        <main className="px-3 sm:px-6 py-6">{children}</main>
      </div>
    </div>
  );
}
