"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { register, login } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Bracket } from "@/lib/bracket";

export default function RegisterPage() {
  const router = useRouter();
  const { refresh } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      await register(email, password);
      await login(email, password);
      await refresh();
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col font-mono">
      <div className="flex-1 max-w-5xl mx-auto w-full border-x border-[#3d3d3a]">
        <header className="px-6 py-3">
          <span className="font-semibold text-[#eab308]">SlowBurnBot</span>
        </header>
        <main className="px-6 py-6">
        <div className="text-[#73726c] mb-4">create account</div>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <div className="text-red-400">{error}</div>}
          <div className="flex items-center gap-2">
            <span className="font-mono text-[#73726c] shrink-0">email</span>
            <input
              type="email"
              placeholder="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="flex-1 bg-transparent border-b border-[#3d3d3a] text-[#f0eee6] placeholder-[#73726c] outline-none focus:border-[#d97757] py-0.5 font-mono transition-colors"
            />
          </div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[#73726c] shrink-0">password</span>
            <input
              type="password"
              placeholder="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              className="flex-1 bg-transparent border-b border-[#3d3d3a] text-[#f0eee6] placeholder-[#73726c] outline-none focus:border-[#d97757] py-0.5 font-mono transition-colors"
            />
          </div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[#73726c] shrink-0">confirm</span>
            <input
              type="password"
              placeholder="confirm password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              minLength={8}
              className="flex-1 bg-transparent border-b border-[#3d3d3a] text-[#f0eee6] placeholder-[#73726c] outline-none focus:border-[#d97757] py-0.5 font-mono transition-colors"
            />
          </div>
          <div className="flex items-center justify-between pt-1">
            <button
              type="submit"
              disabled={loading}
              className="group disabled:opacity-50 transition-colors"
            >
              <Bracket className="text-[#eab308] group-hover:text-white">
                {loading ? "creating…" : "create account"}
              </Bracket>
            </button>
            <Link href="/login" className="text-[#73726c] hover:text-white transition-colors">
              ← sign in
            </Link>
          </div>
        </form>
      </main>
      </div>
    </div>
  );
}
