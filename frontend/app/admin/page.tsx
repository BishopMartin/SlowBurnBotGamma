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
      <h1 className="text-xl font-semibold">Admin — Users</h1>
      {msg && <p className="text-sm text-green-400">{msg}</p>}
      <div className="bg-gray-900 rounded-xl divide-y divide-gray-800">
        {users.map((u) => (
          <div key={u.id} className="px-4 py-3 flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">{u.email}</p>
              <p className="text-xs text-gray-400">
                {u.display_name ?? "—"} · {u.plan_tier} ·{" "}
                {u.is_active ? "active" : "inactive"} · joined{" "}
                {new Date(u.created_at).toLocaleDateString()}
              </p>
            </div>
            <button
              onClick={() => handleSync(u.id)}
              disabled={syncing === u.id}
              className="text-xs bg-gray-800 hover:bg-gray-700 disabled:opacity-50 rounded-lg px-3 py-1.5 transition-colors"
            >
              {syncing === u.id ? "Syncing…" : "Sync Stripe"}
            </button>
          </div>
        ))}
        {users.length === 0 && (
          <p className="px-4 py-6 text-sm text-gray-400 text-center">No users found.</p>
        )}
      </div>
    </div>
  );
}
