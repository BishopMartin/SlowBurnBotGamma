"use client";

import { useEffect, useState } from "react";
import { getUserConfig, updateUserConfig, UserConfig } from "@/lib/api";
import { Bracket } from "@/lib/bracket";
import { Dropdown } from "@/lib/dropdown";

const NOTICES_OPTIONS = [
  { value: "email", label: "email" },
  { value: "text", label: "text" },
  { value: "both", label: "both" },
];

const sectionCls = "border border-[#3d3d3a]";

function formatPhone(raw: string): string {
  const d = raw.replace(/\D/g, "").slice(0, 10);
  if (d.length <= 3) return d;
  if (d.length <= 6) return `(${d.slice(0, 3)}) ${d.slice(3)}`;
  return `(${d.slice(0, 3)}) ${d.slice(3, 6)}-${d.slice(6)}`;
}

function stripPhone(formatted: string): string {
  return formatted.replace(/\D/g, "");
}

export default function ConfigPage() {
  const [config, setConfig] = useState<UserConfig | null>(null);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  // Form state
  const [noticesType, setNoticesType] = useState("email");
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
      <h1 className="font-semibold text-[#f0eee6]">config</h1>

      <div className={sectionCls}>
        <div className="px-4 py-2 border-b border-[#3d3d3a] text-[#73726c]">notifications</div>

        <div className="px-4 py-3 flex items-center gap-x-5 gap-y-2 flex-wrap text-sm">
          <span className="inline-flex items-center gap-1">
            <button
              type="button"
              onClick={() => setNoticesSession(!noticesSession)}
              className="group cursor-pointer transition-colors"
            >
              <Bracket className={noticesSession ? "text-green-400 group-hover:text-red-400" : "text-[#73726c] group-hover:text-green-400"}>
                {noticesSession ? "x" : "\u00a0"}
              </Bracket>
            </button>
            <span className="text-[#73726c]">Session Notifications</span>
          </span>

          <span className="inline-flex items-center gap-0">
            <span className="text-[#73726c]">{"type: "}</span>
            <span className="text-[#f0eee6]">{"["}</span>
            <Dropdown
              value={noticesType}
              onChange={(v) => setNoticesType(v)}
              placeholder="----"
              options={NOTICES_OPTIONS}
            />
            <span className="text-[#f0eee6]">{"]"}</span>
          </span>

          <span className="inline-flex items-center gap-0">
            <span className="text-[#73726c]">{"email: "}</span>
            <span className="text-[#f0eee6]">{"["}</span>
            <input
              type="email"
              value={notifyEmail}
              onChange={(e) => setNotifyEmail(e.target.value)}
              placeholder="email@example.com"
              style={{ width: "20ch" }}
              className="bg-transparent text-[#f0eee6] placeholder-[#73726c] outline-none font-mono min-w-0 px-0"
            />
            <span className="text-[#f0eee6]">{"]"}</span>
          </span>

          <span className="inline-flex items-center gap-0">
            <span className="text-[#73726c]">{"phone: "}</span>
            <span className="text-[#f0eee6]">{"["}</span>
            <input
              type="tel"
              value={formatPhone(notifyPhone)}
              onChange={(e) => setNotifyPhone(stripPhone(e.target.value))}
              placeholder="(123) 456-7890"
              style={{ width: "16ch" }}
              className="bg-transparent text-[#f0eee6] placeholder-[#73726c] outline-none font-mono min-w-0 px-0"
            />
            <span className="text-[#f0eee6]">{"]"}</span>
          </span>
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
