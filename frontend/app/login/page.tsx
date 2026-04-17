"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { login } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

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
      await refresh();
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 font-mono">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-[#d97757] font-semibold text-center" style={{ fontSize: "1.1rem" }}>
          SlowBurnBot
        </div>

        <div className="border border-[#3d3d3a]">
          <div className="px-4 py-2 border-b border-[#3d3d3a] text-[#73726c]">sign in</div>
          <form onSubmit={handleSubmit} className="p-4 space-y-4">
            {error && <div className="text-red-400">{error}</div>}
            <div>
              <div className="text-[#73726c] mb-1">email</div>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full bg-transparent border-b border-[#3d3d3a] text-[#f0eee6] placeholder-[#73726c] outline-none focus:border-[#d97757] py-1 font-mono transition-colors"
              />
            </div>
            <div>
              <div className="text-[#73726c] mb-1">password</div>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full bg-transparent border-b border-[#3d3d3a] text-[#f0eee6] placeholder-[#73726c] outline-none focus:border-[#d97757] py-1 font-mono transition-colors"
              />
            </div>
            <div className="flex items-center justify-between pt-1">
              <button
                type="submit"
                disabled={loading}
                className="text-[#d97757] hover:text-[#f0eee6] disabled:opacity-50 transition-colors"
              >
                {loading ? "[signing in…]" : "[sign in]"}
              </button>
              <Link href="/register" className="text-[#73726c] hover:text-[#d97757] transition-colors">
                register →
              </Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
