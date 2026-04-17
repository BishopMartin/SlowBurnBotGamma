"use client";

import { useEffect, useState } from "react";
import { adminListUsers, adminSyncSubscription, AdminUser } from "@/lib/api";

export default function AdminPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [syncing, setSyncing] = useState<string | null>(null);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    adminListUsers().then(setUsers).catch(() => {});
  }, []);

  async function handleSync(userId: string) {
    setSyncing(userId);
    setMsg("");
    try {
      const res = await adminSyncSubscription(userId) as { status: string };
      setMsg(`Synced — status: ${res.status}`);
    } catch (err: unknown) {
      setMsg(err instanceof Error ? err.message : "Sync failed.");
    } finally {
      setSyncing(null);
    }
  }

  return (
    <div className="space-y-6 p-6 max-w-5xl mx-auto">
      <h1 className="font-semibold text-[#f0eee6]">Admin — Users</h1>
      {msg && <p className="text-green-400">{msg}</p>}
      <div className="bg-[#1f1e1d] rounded-xl divide-y divide-[#3d3d3a] border border-[#3d3d3a]" style={{ boxShadow: "0 1px 2px rgba(0,0,0,0.08)" }}>
        {users.map((u) => (
          <div key={u.id} className="px-4 py-3 flex items-center justify-between">
            <div>
              <p className="font-medium text-[#f0eee6]">{u.email}</p>
              <p className="text-[#73726c]">
                {u.display_name ?? "—"} · {u.plan_tier} ·{" "}
                {u.is_active ? "active" : "inactive"} · joined{" "}
                {new Date(u.created_at).toLocaleDateString()}
              </p>
            </div>
            <button
              onClick={() => handleSync(u.id)}
              disabled={syncing === u.id}
              className="bg-[#262624] hover:bg-[#3d3d3a] disabled:opacity-50 rounded-lg px-3 py-1.5 text-[#bfbdb4] transition-colors border border-[#3d3d3a]"
            >
              {syncing === u.id ? "Syncing…" : "Sync Stripe"}
            </button>
          </div>
        ))}
        {users.length === 0 && (
          <p className="px-4 py-6 text-[#73726c] text-center">No users found.</p>
        )}
      </div>
    </div>
  );
}
