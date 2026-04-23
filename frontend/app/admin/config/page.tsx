"use client";

import { useEffect, useState } from "react";
import {
  adminGetNotificationCredentials,
  adminUpdateNotificationCredentials,
  NotificationCredentials,
} from "@/lib/api";
import { Bracket } from "@/lib/bracket";

const sectionCls = "border border-[#3d3d3a]";

export default function AdminConfigPage() {
  const [creds, setCreds] = useState<NotificationCredentials | null>(null);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  // Form state
  const [smtpServer, setSmtpServer] = useState("");
  const [smtpPort, setSmtpPort] = useState("587");
  const [smtpUser, setSmtpUser] = useState("");
  const [smtpPassword, setSmtpPassword] = useState("");
  const [textbeltKey, setTextbeltKey] = useState("");
  const [editingSmtpPassword, setEditingSmtpPassword] = useState(false);
  const [editingTextbeltKey, setEditingTextbeltKey] = useState(false);

  useEffect(() => {
    adminGetNotificationCredentials()
      .then((c) => {
        setCreds(c);
        setSmtpServer(c.smtp_server || "");
        setSmtpPort(String(c.smtp_port));
        setSmtpUser(c.smtp_user || "");
      })
      .catch(() => {});
  }, []);

  async function handleSave() {
    setSaving(true);
    setMsg("");
    try {
      const data: Record<string, string | number> = {
        smtp_server: smtpServer,
        smtp_port: parseInt(smtpPort, 10) || 587,
        smtp_user: smtpUser,
      };
      if (smtpPassword) data.smtp_password = smtpPassword;
      if (textbeltKey) data.textbelt_key = textbeltKey;

      const updated = await adminUpdateNotificationCredentials(data);
      setCreds(updated);
      setSmtpPassword("");
      setTextbeltKey("");
      setEditingSmtpPassword(false);
      setEditingTextbeltKey(false);
      setMsg("saved.");
    } catch (err: unknown) {
      setMsg(err instanceof Error ? err.message : "save failed.");
    } finally {
      setSaving(false);
    }
  }

  if (!creds) {
    return <div className="font-mono text-[#73726c]">loading…</div>;
  }

  return (
    <div className="space-y-6 font-mono">
      <h1 className="font-semibold text-[#f0eee6]">admin — Config</h1>

      <div className={sectionCls}>
        <div className="px-4 py-2 border-b border-[#3d3d3a] text-[#73726c]">Notification Settings</div>

        {/* SMTP row */}
        <div className="px-4 py-3 flex items-center gap-x-5 gap-y-2 flex-wrap text-sm border-b border-[#3d3d3a]">
          <span className="text-[#73726c]" style={{ width: "8ch" }}>smtp:</span>

          <span className="inline-flex items-center gap-0">
            <span className="text-[#73726c]">{"server: "}</span>
            <span className="text-[#f0eee6]">{"["}</span>
            <input
              type="text"
              value={smtpServer}
              onChange={(e) => setSmtpServer(e.target.value)}
              placeholder="----"
              style={{ width: "18ch" }}
              className="bg-transparent text-[#f0eee6] placeholder-[#73726c] outline-none font-mono min-w-0 px-0"
            />
            <span className="text-[#f0eee6]">{"]"}</span>
          </span>

          <span className="inline-flex items-center gap-0">
            <span className="text-[#73726c]">{"port: "}</span>
            <span className="text-[#f0eee6]">{"["}</span>
            <input
              type="text"
              inputMode="numeric"
              value={smtpPort}
              onChange={(e) => setSmtpPort(e.target.value.replace(/\D/g, ""))}
              placeholder="----"
              style={{ width: "4ch" }}
              className="bg-transparent text-[#f0eee6] placeholder-[#73726c] outline-none font-mono min-w-0 px-0 text-center"
            />
            <span className="text-[#f0eee6]">{"]"}</span>
          </span>

          <span className="inline-flex items-center gap-0">
            <span className="text-[#73726c]">{"user: "}</span>
            <span className="text-[#f0eee6]">{"["}</span>
            <input
              type="text"
              value={smtpUser}
              onChange={(e) => setSmtpUser(e.target.value)}
              placeholder="----"
              style={{ width: "20ch" }}
              className="bg-transparent text-[#f0eee6] placeholder-[#73726c] outline-none font-mono min-w-0 px-0"
            />
            <span className="text-[#f0eee6]">{"]"}</span>
          </span>

          <span className="inline-flex items-center gap-0">
            <span className="text-[#73726c]">{"password: "}</span>
            <span className="text-[#f0eee6]">{"["}</span>
            {editingSmtpPassword ? (
              <input
                type="text"
                value={smtpPassword}
                onChange={(e) => setSmtpPassword(e.target.value)}
                placeholder="----"
                autoFocus
                onBlur={() => { if (!smtpPassword) setEditingSmtpPassword(false); }}
                style={{ width: "14ch" }}
                className="bg-transparent text-[#f0eee6] placeholder-[#73726c] outline-none font-mono min-w-0 pl-1"
              />
            ) : (
              <button
                type="button"
                onClick={() => setEditingSmtpPassword(true)}
                style={{ width: "14ch" }}
                className="bg-transparent text-left font-mono min-w-0 pl-1 cursor-pointer inline-flex items-center translate-y-px"
              >
                <span className={creds.smtp_password_set ? "text-[#f0eee6]" : "text-[#73726c]"}>
                  {creds.smtp_password_set ? " " + "*".repeat(13) : "----"}
                </span>
              </button>
            )}
            <span className="text-[#f0eee6]">{"]"}</span>
          </span>
        </div>

        {/* TextBelt row */}
        <div className="px-4 py-3 flex items-center gap-x-5 gap-y-2 flex-wrap text-sm">
          <span className="text-[#73726c]" style={{ width: "8ch" }}>textbelt:</span>

          <span className="inline-flex items-center gap-0">
            <span className="text-[#73726c]">{"api key: "}</span>
            <span className="text-[#f0eee6]">{"["}</span>
            {editingTextbeltKey ? (
              <input
                type="text"
                value={textbeltKey}
                onChange={(e) => setTextbeltKey(e.target.value)}
                placeholder="----"
                autoFocus
                onBlur={() => { if (!textbeltKey) setEditingTextbeltKey(false); }}
                style={{ width: "20ch" }}
                className="bg-transparent text-[#f0eee6] placeholder-[#73726c] outline-none font-mono min-w-0 pl-1"
              />
            ) : (
              <button
                type="button"
                onClick={() => setEditingTextbeltKey(true)}
                style={{ width: "20ch" }}
                className="bg-transparent text-left font-mono min-w-0 pl-1 cursor-pointer inline-flex items-center translate-y-px"
              >
                <span className={creds.textbelt_key_set ? "text-[#f0eee6]" : "text-[#73726c]"}>
                  {creds.textbelt_key_set ? " " + "*".repeat(19) : "----"}
                </span>
              </button>
            )}
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
        {msg && <span className="text-status-ok">{msg}</span>}
      </div>
    </div>
  );
}
