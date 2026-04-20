"use client";

import { useEffect, useState } from "react";
import { getUserConfig, updateUserConfig, UserConfig } from "@/lib/api";
import { Bracket } from "@/lib/bracket";
import { Dropdown } from "@/lib/dropdown";

const NOTICES_OPTIONS = [
  { value: "none", label: "none" },
  { value: "email", label: "email" },
  { value: "text", label: "text" },
  { value: "both", label: "both" },
];

const sectionCls = "border border-[#3d3d3a]";

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
      <h1 className="font-semibold text-[#f0eee6]">config</h1>

      <div className={sectionCls}>
        <div className="px-4 py-2 border-b border-[#3d3d3a] text-[#73726c]">notifications</div>

        {/* Row 1: type + enabled */}
        <div className="px-4 py-3 flex items-center gap-x-5 gap-y-2 flex-wrap text-sm border-b border-[#3d3d3a]">
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

          <span className="inline-flex items-center gap-1">
            <span className="text-[#73726c]">session notices:</span>
            <button
              type="button"
              onClick={() => setNoticesSession(!noticesSession)}
              className="group cursor-pointer transition-colors"
            >
              <Bracket className={noticesSession ? "text-green-400 group-hover:text-red-400" : "text-[#73726c] group-hover:text-green-400"}>
                {noticesSession ? "x" : "\u00a0"}
              </Bracket>
            </button>
          </span>
        </div>

        {/* Row 2: email + phone */}
        <div className="px-4 py-3 flex items-center gap-x-5 gap-y-2 flex-wrap text-sm">
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
              value={notifyPhone}
              onChange={(e) => setNotifyPhone(e.target.value)}
              placeholder="1234567890"
              style={{ width: "12ch" }}
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
