"use client";

import { useEffect, useState } from "react";
import { getUserConfig, updateUserConfig, UserConfig } from "@/lib/api";
import { Bracket } from "@/lib/bracket";

const NOTICES_OPTIONS = [
  { value: "none", label: "none" },
  { value: "email", label: "email" },
  { value: "text", label: "text" },
  { value: "both", label: "both" },
];

export default function ConfigPage() {
  const [config, setConfig] = useState<UserConfig | null>(null);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  // Form state
  const [noticesType, setNoticesType] = useState("none");
  const [noticesSession, setNoticesSession] = useState(true);
  const [notifyEmail, setNotifyEmail] = useState("");
  const [notifyPhone, setNotifyPhone] = useState("");

  useEffect(() => {
    getUserConfig()
      .then((c) => {
        setConfig(c);
        setNoticesType(c.notices_type);
        setNoticesSession(c.notices_session);
        setNotifyEmail(c.notify_email ?? "");
        setNotifyPhone(c.notify_phone ?? "");
      })
      .catch(() => {});
  }, []);

  async function handleSave() {
    setSaving(true);
    setMsg("");
    try {
      const updated = await updateUserConfig({
        notices_type: noticesType,
        notices_session: noticesSession,
        notify_email: notifyEmail || null,
        notify_phone: notifyPhone || null,
      });
      setConfig(updated);
      setMsg("saved.");
    } catch (err: unknown) {
      setMsg(err instanceof Error ? err.message : "save failed.");
    } finally {
      setSaving(false);
    }
  }

  if (!config) {
    return <div className="font-mono text-[#73726c]">loading…</div>;
  }

  return (
    <div className="space-y-6 font-mono">
      <h1 className="font-semibold text-[#f0eee6]">config — notifications</h1>

      <div className="border border-[#3d3d3a] divide-y divide-[#3d3d3a]">
        {/* Notification type */}
        <div className="flex items-center justify-between px-4 py-3">
          <span className="text-[#bfbdb4]">notification type</span>
          <select
            value={noticesType}
            onChange={(e) => setNoticesType(e.target.value)}
            className="bg-[#1a1a18] border border-[#3d3d3a] text-[#f0eee6] px-3 py-1 rounded-none outline-none focus:border-[#d97757] transition-colors"
          >
            {NOTICES_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Session activity notices */}
        <div className="flex items-center justify-between px-4 py-3">
          <span className="text-[#bfbdb4]">session activity notices</span>
          <button
            onClick={() => setNoticesSession(!noticesSession)}
            className="group cursor-pointer transition-colors"
          >
            <Bracket className={noticesSession ? "text-green-400 group-hover:text-red-400" : "text-[#73726c] group-hover:text-green-400"}>
              {noticesSession ? "x" : "\u00a0"}
            </Bracket>
          </button>
        </div>

        {/* Notification email */}
        <div className="flex items-center justify-between px-4 py-3">
          <span className="text-[#bfbdb4]">notification email</span>
          <input
            type="email"
            value={notifyEmail}
            onChange={(e) => setNotifyEmail(e.target.value)}
            placeholder="email@example.com"
            className="bg-transparent border-b border-[#3d3d3a] text-[#f0eee6] placeholder-[#3d3d3a] outline-none focus:border-[#d97757] py-0.5 w-64 text-right transition-colors"
          />
        </div>

        {/* Notification phone */}
        <div className="flex items-center justify-between px-4 py-3">
          <span className="text-[#bfbdb4]">notification phone</span>
          <input
            type="tel"
            value={notifyPhone}
            onChange={(e) => setNotifyPhone(e.target.value)}
            placeholder="1234567890"
            className="bg-transparent border-b border-[#3d3d3a] text-[#f0eee6] placeholder-[#3d3d3a] outline-none focus:border-[#d97757] py-0.5 w-64 text-right transition-colors"
          />
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button
          onClick={handleSave}
          disabled={saving}
          className="group disabled:opacity-50 transition-colors"
        >
          <Bracket className="text-[#d97757] group-hover:text-[#f0eee6]">
            {saving ? "saving…" : "save"}
          </Bracket>
        </button>
        {msg && <span className="text-green-400">{msg}</span>}
      </div>
    </div>
  );
}
