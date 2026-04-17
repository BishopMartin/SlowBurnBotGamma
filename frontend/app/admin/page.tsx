"use client";

import { useEffect, useState } from "react";
import { adminListUsers, adminSyncSubscription, AdminUser } from "@/lib/api";
import { Bracket } from "@/lib/bracket";

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
      setMsg(`synced — status: ${res.status}`);
    } catch (err: unknown) {
      setMsg(err instanceof Error ? err.message : "sync failed.");
    } finally {
      setSyncing(null);
    }
  }

  return (
    <div className="space-y-4 font-mono">
      <h1 className="font-semibold text-[#f0eee6]">admin — users</h1>
      {msg && <p className="text-green-400">{msg}</p>}
      <div className="border border-[#3d3d3a]">
        {users.length === 0 ? (
          <p className="px-4 py-6 text-[#73726c]">no users found.</p>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="text-left text-[#73726c] border-b border-[#3d3d3a]">
                <th className="px-4 py-2 font-normal">email</th>
                <th className="px-4 py-2 font-normal">plan</th>
                <th className="px-4 py-2 font-normal">status</th>
                <th className="px-4 py-2 font-normal">joined</th>
                <th className="px-4 py-2 font-normal"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#3d3d3a]">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-[#1f1e1d] transition-colors">
                  <td className="px-4 py-2 text-[#f0eee6]">{u.email}</td>
                  <td className="px-4 py-2 text-[#bfbdb4]">{u.plan_tier}</td>
                  <td className="px-4 py-2">
                    <Bracket className={u.is_active ? "text-green-400" : "text-[#73726c]"}>
                      {u.is_active ? "active" : "inactive"}
                    </Bracket>
                  </td>
                  <td className="px-4 py-2 text-[#73726c]">
                    {new Date(u.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <button
                      onClick={() => handleSync(u.id)}
                      disabled={syncing === u.id}
                      className="group disabled:opacity-50 transition-colors"
                    >
                      <Bracket className="text-[#d97757] group-hover:text-[#f0eee6]">
                        {syncing === u.id ? "syncing…" : "sync stripe"}
                      </Bracket>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
