"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && (!user || !user.is_superuser)) router.push("/dashboard");
  }, [user, loading, router]);

  if (loading || !user?.is_superuser) return null;
  return (
    <div className="space-y-4">
      <nav className="flex gap-4 font-mono text-sm border-b border-[#3d3d3a] pb-3">
        <span className="text-[#73726c]">admin:</span>
        <a href="/admin" className="text-[#bfbdb4] hover:text-[#f0eee6] transition-colors">[users]</a>
        <a href="/admin/accounts" className="text-[#bfbdb4] hover:text-[#f0eee6] transition-colors">[accounts]</a>
      </nav>
      {children}
    </div>
  );
}
