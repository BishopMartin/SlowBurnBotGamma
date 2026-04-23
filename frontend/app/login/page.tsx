"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { login } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Bracket } from "@/lib/bracket";

export default function LoginPage() {
  const router = useRouter();
  const { refresh } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      const user = await refresh();
      router.push(user?.is_superuser ? "/admin" : "/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col font-mono">
      <div className="flex-1 max-w-5xl mx-auto w-full border-x border-[#3d3d3a]">
        <header className="px-6 py-3">
          <span className="font-semibold text-[#d97757]">SlowBurnBot</span>
        </header>
        <main className="px-6 py-6">
        <div className="text-[#B1ADA1] mb-4">sign in</div>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <div className="text-status-bad">{error}</div>}
          <div className="flex items-center gap-2">
            <span className="font-mono text-[#B1ADA1] shrink-0">email</span>
            <input
              type="email"
              placeholder="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="flex-1 bg-transparent border-b border-[#3d3d3a] text-[#f0eee6] placeholder-[#B1ADA1] outline-none focus:border-[#d97757] py-0.5 font-mono transition-colors"
            />
          </div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[#B1ADA1] shrink-0">password</span>
            <input
              type="password"
              placeholder="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="flex-1 bg-transparent border-b border-[#3d3d3a] text-[#f0eee6] placeholder-[#B1ADA1] outline-none focus:border-[#d97757] py-0.5 font-mono transition-colors"
            />
          </div>
          <div className="flex items-center justify-between pt-1">
            <button
              type="submit"
              disabled={loading}
              className="group disabled:opacity-50 transition-colors"
            >
              <Bracket className="text-[#d97757] group-hover:text-[#f0eee6]">
                {loading ? "signing in…" : "sign in"}
              </Bracket>
            </button>
            <Link href="/register" className="text-[#B1ADA1] hover:text-[#d97757] transition-colors">
              register →
            </Link>
          </div>
        </form>
      </main>
      </div>
    </div>
  );
}
