"use client";

import { useEffect, useState } from "react";
import { getUserConfig, updateUserConfig, UserConfig } from "@/lib/api";
import { Bracket } from "@/lib/bracket";
import { Dropdown } from "@/lib/dropdown";
import { NumberInput } from "@/lib/number-input";

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

  // Session settings
  const [likeSuggested, setLikeSuggested] = useState(false);
  const [likeSponsored, setLikeSponsored] = useState(false);
  const [skipLoginCheck, setSkipLoginCheck] = useState(false);
  const [loginTries, setLoginTries] = useState(3);

  // Notification settings
  const [noticesType, setNoticesType] = useState("email");
  const [noticesSession, setNoticesSession] = useState(true);
  const [notifyEmail, setNotifyEmail] = useState("");
  const [notifyPhone, setNotifyPhone] = useState("");

  useEffect(() => {
    getUserConfig()
      .then((c) => {
        setConfig(c);
        setLikeSuggested(c.like_suggested);
        setLikeSponsored(c.like_sponsored);
        setSkipLoginCheck(c.skip_login_check);
        setLoginTries(c.login_tries);
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
        like_suggested: likeSuggested,
        like_sponsored: likeSponsored,
        skip_login_check: skipLoginCheck,
        login_tries: loginTries,
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
    return <div className="font-mono text-[#B1ADA1]">loading…</div>;
  }

  return (
    <div className="space-y-6 font-mono">
      <h1 className="font-semibold text-[#f4f3ee]">Config</h1>

      <div className={sectionCls}>
        <div className="px-4 py-2 border-b border-[#3d3d3a] text-[#B1ADA1]">session settings</div>

        <div className="px-4 py-3 flex items-center gap-x-5 gap-y-2 flex-wrap text-sm">
          <span className="inline-flex items-center gap-1">
            <button
              type="button"
              onClick={() => setLikeSuggested(!likeSuggested)}
              className="group cursor-pointer transition-colors"
            >
              <Bracket className={likeSuggested ? "text-status-ok group-hover:text-status-bad" : "text-[#B1ADA1] group-hover:text-status-ok"}>
                {likeSuggested ? "x" : "\u00a0"}
              </Bracket>
            </button>
            <span className="text-[#B1ADA1]">Like Suggested</span>
          </span>

          <span className="inline-flex items-center gap-1">
            <button
              type="button"
              onClick={() => setLikeSponsored(!likeSponsored)}
              className="group cursor-pointer transition-colors"
            >
              <Bracket className={likeSponsored ? "text-status-ok group-hover:text-status-bad" : "text-[#B1ADA1] group-hover:text-status-ok"}>
                {likeSponsored ? "x" : "\u00a0"}
              </Bracket>
            </button>
            <span className="text-[#B1ADA1]">Like Sponsored</span>
          </span>

          <span className="inline-flex items-center gap-1">
            <button
              type="button"
              onClick={() => setSkipLoginCheck(!skipLoginCheck)}
              className="group cursor-pointer transition-colors"
            >
              <Bracket className={skipLoginCheck ? "text-status-ok group-hover:text-status-bad" : "text-[#B1ADA1] group-hover:text-status-ok"}>
                {skipLoginCheck ? "x" : "\u00a0"}
              </Bracket>
            </button>
            <span className="text-[#B1ADA1]">Skip Login Check</span>
          </span>

          <span className="inline-flex items-center gap-0">
            <span className="text-[#B1ADA1]">{"login tries: "}</span>
            <span className="text-[#f4f3ee]">{"["}</span>
            <NumberInput
              value={loginTries}
              onChange={(n) => setLoginTries(n || 1)}
              placeholder="3"
              max={10}
              maxLength={2}
            />
            <span className="text-[#f4f3ee]">{"]"}</span>
          </span>
        </div>
      </div>

      <div className={sectionCls}>
        <div className="px-4 py-2 border-b border-[#3d3d3a] text-[#B1ADA1]">notifications</div>

        <div className="px-4 py-3 flex items-center gap-x-5 gap-y-2 flex-wrap text-sm">
          <span className="inline-flex items-center gap-1">
            <button
              type="button"
              onClick={() => setNoticesSession(!noticesSession)}
              className="group cursor-pointer transition-colors"
            >
              <Bracket className={noticesSession ? "text-status-ok group-hover:text-status-bad" : "text-[#B1ADA1] group-hover:text-status-ok"}>
                {noticesSession ? "x" : "\u00a0"}
              </Bracket>
            </button>
            <span className="text-[#B1ADA1]">Session Notifications</span>
          </span>

          <span className="inline-flex items-center gap-0">
            <span className="text-[#B1ADA1]">{"type: "}</span>
            <span className="text-[#f4f3ee]">{"["}</span>
            <Dropdown
              value={noticesType}
              onChange={(v) => setNoticesType(v)}
              placeholder="----"
              options={NOTICES_OPTIONS}
            />
            <span className="text-[#f4f3ee]">{"]"}</span>
          </span>

          <span className="inline-flex items-center gap-0">
            <span className="text-[#B1ADA1]">{"email: "}</span>
            <span className="text-[#f4f3ee]">{"["}</span>
            <input
              type="email"
              value={notifyEmail}
              onChange={(e) => setNotifyEmail(e.target.value)}
              placeholder="email@example.com"
              style={{ width: "20ch" }}
              className="bg-transparent text-[#f4f3ee] placeholder-[#B1ADA1] outline-none font-mono min-w-0 px-0"
            />
            <span className="text-[#f4f3ee]">{"]"}</span>
          </span>

          <span className="inline-flex items-center gap-0">
            <span className="text-[#B1ADA1]">{"phone: "}</span>
            <span className="text-[#f4f3ee]">{"["}</span>
            <input
              type="tel"
              value={formatPhone(notifyPhone)}
              onChange={(e) => setNotifyPhone(stripPhone(e.target.value))}
              placeholder="(123) 456-7890"
              style={{ width: "16ch" }}
              className="bg-transparent text-[#f4f3ee] placeholder-[#B1ADA1] outline-none font-mono min-w-0 px-0"
            />
            <span className="text-[#f4f3ee]">{"]"}</span>
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button
          onClick={handleSave}
          disabled={saving}
          className="group disabled:opacity-50 transition-colors"
        >
          <Bracket className="text-[#d97757] group-hover:text-[#f4f3ee]">
            {saving ? "saving…" : "save"}
          </Bracket>
        </button>
        {msg && <span className="text-status-ok">{msg}</span>}
      </div>
    </div>
  );
}
