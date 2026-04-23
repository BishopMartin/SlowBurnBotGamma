"use client";

import { useEffect, useState } from "react";
import {
  adminListUsers,
  adminSyncSubscription,
  adminActivateSubscription,
  adminDeactivateSubscription,
  AdminUser,
} from "@/lib/api";
import { Bracket } from "@/lib/bracket";

export default function AdminPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState("");

  async function loadUsers() {
    adminListUsers().then(setUsers).catch(() => {});
  }

  useEffect(() => {
    loadUsers();
  }, []);

  async function handleSync(userId: string) {
    setBusy(userId);
    setMsg("");
    try {
      const res = await adminSyncSubscription(userId) as { status: string };
      setMsg(`synced — status: ${res.status}`);
      await loadUsers();
    } catch (err: unknown) {
      setMsg(err instanceof Error ? err.message : "sync failed.");
    } finally {
      setBusy(null);
    }
  }

  async function handleToggleSubscription(user: AdminUser) {
    setBusy(user.id);
    setMsg("");
    try {
      const action = user.subscription_status === "active"
        ? adminDeactivateSubscription
        : adminActivateSubscription;
      const res = await action(user.id);
      setMsg(`${user.email} — ${res.status} / ${res.plan_tier}`);
      await loadUsers();
    } catch (err: unknown) {
      setMsg(err instanceof Error ? err.message : "toggle failed.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-4 font-mono">
      <h1 className="font-semibold text-[#f4f3ee]">admin — users</h1>
      {msg && <p className="text-status-ok">{msg}</p>}
      <div className="border border-[#3d3d3a]">
        {users.length === 0 ? (
          <p className="px-4 py-6 text-[#B1ADA1]">no users found.</p>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="text-left text-[#B1ADA1] border-b border-[#3d3d3a]">
                <th className="px-4 py-2 font-normal">email</th>
                <th className="px-4 py-2 font-normal">plan</th>
                <th className="px-4 py-2 font-normal">subscription</th>
                <th className="px-4 py-2 font-normal">joined</th>
                <th className="px-4 py-2 font-normal"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#3d3d3a]">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-[#1f1e1d] transition-colors">
                  <td className="px-4 py-2 text-[#f4f3ee]">{u.email}</td>
                  <td className="px-4 py-2 text-[#bfbdb4]">{u.plan_tier}</td>
                  <td className="px-4 py-2">
                    <Bracket className={u.subscription_status === "active" ? "text-status-ok" : "text-[#B1ADA1]"}>
                      {u.subscription_status}
                    </Bracket>
                  </td>
                  <td className="px-4 py-2 text-[#B1ADA1]">
                    {new Date(u.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-2 text-right space-x-2">
                    <button
                      onClick={() => handleToggleSubscription(u)}
                      disabled={busy === u.id}
                      className="group disabled:opacity-50 transition-colors"
                    >
                      <Bracket className={u.subscription_status === "active" ? "text-[#B1ADA1] group-hover:text-[#f4f3ee]" : "text-status-ok group-hover:text-[#f4f3ee]"}>
                        {busy === u.id ? "…" : u.subscription_status === "active" ? "deactivate" : "activate"}
                      </Bracket>
                    </button>
                    <button
                      onClick={() => handleSync(u.id)}
                      disabled={busy === u.id}
                      className="group disabled:opacity-50 transition-colors"
                    >
                      <Bracket className="text-[#d97757] group-hover:text-[#f4f3ee]">
                        {busy === u.id ? "…" : "sync stripe"}
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
