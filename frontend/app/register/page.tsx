"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { register, login } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function RegisterPage() {
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
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <h1 className="font-bold mb-8 text-center text-[#d97757]" style={{ fontSize: "1.25rem" }}>SlowBurnBot</h1>
        <form onSubmit={handleSubmit} className="bg-[#1f1e1d] rounded-xl p-6 space-y-4 border border-[#3d3d3a]" style={{ boxShadow: "0 6px 16px -4px rgba(0,0,0,0.12)" }}>
          <h2 className="font-semibold text-[#f0eee6]">Create account</h2>
          {error && <p className="text-red-400">{error}</p>}
          <div>
            <label className="block text-[#bfbdb4] mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full bg-[#262624] rounded-lg px-3 py-2 text-[#f0eee6] placeholder-[#73726c] outline-none border border-[#3d3d3a] focus:border-[#d97757] focus:ring-1 focus:ring-[#d97757] transition-colors"
            />
          </div>
          <div>
            <label className="block text-[#bfbdb4] mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              className="w-full bg-[#262624] rounded-lg px-3 py-2 text-[#f0eee6] placeholder-[#73726c] outline-none border border-[#3d3d3a] focus:border-[#d97757] focus:ring-1 focus:ring-[#d97757] transition-colors"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#c6613f] hover:bg-[#d97757] disabled:opacity-50 rounded-lg px-4 py-2 font-medium text-[#f0eee6] transition-colors"
          >
            {loading ? "Creating account…" : "Create account"}
          </button>
          <p className="text-center text-[#73726c]">
            Already have an account?{" "}
            <Link href="/login" className="text-[#d97757] hover:underline">
              Sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
