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
      <header className="border-b border-[#3d3d3a] px-6 py-3">
        <span className="font-semibold text-[#d97757]">SlowBurnBot</span>
      </header>
      <main className="flex-1 p-6 max-w-5xl mx-auto w-full">
        <div className="border border-[#3d3d3a]">
          <div className="px-4 py-2 border-b border-[#3d3d3a] text-[#73726c]">create account</div>
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
                minLength={8}
                className="w-full bg-transparent border-b border-[#3d3d3a] text-[#f0eee6] placeholder-[#73726c] outline-none focus:border-[#d97757] py-1 font-mono transition-colors"
              />
            </div>
            <div>
              <div className="text-[#73726c] mb-1">confirm password</div>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                minLength={8}
                className="w-full bg-transparent border-b border-[#3d3d3a] text-[#f0eee6] placeholder-[#73726c] outline-none focus:border-[#d97757] py-1 font-mono transition-colors"
              />
            </div>
            <div className="flex items-center justify-between pt-1">
              <button
                type="submit"
                disabled={loading}
                className="group disabled:opacity-50 transition-colors"
              >
                <Bracket className="text-[#d97757] group-hover:text-[#f0eee6]">
                  {loading ? "creating…" : "create account"}
                </Bracket>
              </button>
              <Link href="/login" className="text-[#73726c] hover:text-[#d97757] transition-colors">
                ← sign in
              </Link>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}
