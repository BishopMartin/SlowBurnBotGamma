"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { logout } from "@/lib/api";
import { Bracket } from "@/lib/bracket";
import { APP_VERSION } from "@/lib/version";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const navItems = [
    { href: "/admin", label: "[users]" },
    { href: "/admin/accounts", label: "[accounts]" },
  ];

  useEffect(() => {
    if (!loading && (!user || !user.is_superuser)) router.push("/dashboard");
  }, [user, loading, router]);

  if (loading || !user?.is_superuser) return null;

  async function handleLogout() {
    await logout();
    router.push("/login");
  }

  const headerAdminActive =
    pathname !== "/admin/config" && (pathname === "/admin" || pathname.startsWith("/admin/"));
  const headerConfigActive = pathname === "/admin/config";

  function subNavUsersActive() {
    return pathname === "/admin";
  }

  function subNavAccountsActive() {
    return pathname === "/admin/accounts" || pathname.startsWith("/admin/accounts/");
  }

  return (
    <div className="min-h-screen flex flex-col font-mono">
      <div className="flex-1 max-w-5xl mx-auto w-full border-x border-[#3d3d3a]">
        <header className="px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <span className="font-semibold text-[#d97757]">SlowBurnBot</span>
            <span className="text-[#3d3d3a]">--</span>
            <Link
              href="/admin"
              className={`transition-colors ${
                headerAdminActive ? "text-[#d97757]" : "text-[#73726c] hover:text-white"
              }`}
            >
              [admin]
            </Link>
            <Link
              href="/admin/config"
              className={`transition-colors ${
                headerConfigActive ? "text-[#d97757]" : "text-[#73726c] hover:text-white"
              }`}
            >
              [config]
            </Link>
          </div>
          <div className="flex items-center gap-4">
            <button onClick={() => window.location.reload()} className="text-[#3d3d3a] hover:text-[#73726c] cursor-pointer transition-colors" title="Click to reload">v{APP_VERSION}</button>
            <span className="text-[#eab308]">{user.email}</span>
            <button onClick={handleLogout} className="group transition-colors">
              <Bracket className="text-[#73726c] group-hover:text-[#d97757]">sign out</Bracket>
            </button>
          </div>
        </header>
        <main className="px-6 py-6 space-y-4">
          <nav className="flex gap-4 text-sm border-b border-[#3d3d3a] pb-3">
            <span className="text-[#73726c]">admin:</span>
            {navItems.map((item) => {
              const active =
                item.href === "/admin"
                  ? subNavUsersActive()
                  : subNavAccountsActive();
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`transition-colors ${
                    active ? "text-[#d97757]" : "text-[#73726c] hover:text-white"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
          {children}
        </main>
      </div>
    </div>
  );
}
