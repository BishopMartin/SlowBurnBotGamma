"use client";

import { useEffect, useState } from "react";
import { getUserConfig, updateUserConfig, getIgnoreHandles, updateIgnoreHandles, UserConfig } from "@/lib/api";
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
  const [noticesLogin, setNoticesLogin] = useState(true);
  const [notifyEmail, setNotifyEmail] = useState("");
  const [notifyPhone, setNotifyPhone] = useState("");

  // Ignore list
  const [ignoreHandles, setIgnoreHandles] = useState("");

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
        setNoticesLogin(c.notices_login);
        setNotifyEmail(c.notify_email ?? "");
        setNotifyPhone(c.notify_phone ?? "");
      })
      .catch(() => {});
    getIgnoreHandles()
      .then((r) => setIgnoreHandles(r.handles.join(", ")))
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
        notices_login: noticesLogin,
        notify_email: notifyEmail || null,
        notify_phone: notifyPhone || null,
      });
      setConfig(updated);
      const handles = ignoreHandles.split(",").map((h) => h.trim()).filter(Boolean);
      const result = await updateIgnoreHandles(handles);
      setIgnoreHandles(result.handles.join(", "));
      setMsg("saved.");
    } catch (err: unknown) {
      setMsg(err instanceof Error ? err.message : "save failed.");
    } finally {
      setSaving(false);
    }
  }

  if (!config) {
    return <div className="font-mono text-[#9A968B]">loading…</div>;
  }

  return (
    <div className="space-y-6 font-mono">
      <h1 className="font-semibold text-[#f4f3ee]">Config</h1>

      <div className={sectionCls}>
        <div className="px-4 py-2 border-b border-[#3d3d3a] text-[#9A968B] bg-[#1a1918]">session settings</div>

        <div className="px-4 py-3 flex items-center gap-x-5 gap-y-2 flex-wrap text-sm">
          <span className="inline-flex items-center gap-1">
            <button
              type="button"
              onClick={() => setLikeSuggested(!likeSuggested)}
              className="group cursor-pointer transition-colors"
            >
              <Bracket className={likeSuggested ? "text-status-ok group-hover:text-status-bad" : "text-[#9A968B] group-hover:text-status-ok"}>
                {likeSuggested ? "x" : "\u00a0"}
              </Bracket>
            </button>
            <span className="text-[#9A968B]">Like Suggested</span>
          </span>

          <span className="inline-flex items-center gap-1">
            <button
              type="button"
              onClick={() => setLikeSponsored(!likeSponsored)}
              className="group cursor-pointer transition-colors"
            >
              <Bracket className={likeSponsored ? "text-status-ok group-hover:text-status-bad" : "text-[#9A968B] group-hover:text-status-ok"}>
                {likeSponsored ? "x" : "\u00a0"}
              </Bracket>
            </button>
            <span className="text-[#9A968B]">Like Sponsored</span>
          </span>

          <span className="inline-flex items-center gap-1">
            <button
              type="button"
              onClick={() => setSkipLoginCheck(!skipLoginCheck)}
              className="group cursor-pointer transition-colors"
            >
              <Bracket className={skipLoginCheck ? "text-status-ok group-hover:text-status-bad" : "text-[#9A968B] group-hover:text-status-ok"}>
                {skipLoginCheck ? "x" : "\u00a0"}
              </Bracket>
            </button>
            <span className="text-[#9A968B]">Skip Login Check</span>
          </span>

          <span className="inline-flex items-center gap-0">
            <span className="text-[#9A968B]">{"login tries: "}</span>
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
        <div className="px-4 py-2 border-b border-[#3d3d3a] text-[#9A968B] bg-[#1a1918]">notifications</div>

        <div className="px-4 py-3 flex items-center gap-x-5 gap-y-2 flex-wrap text-sm">
          <span className="inline-flex items-center gap-1">
            <button
              type="button"
              onClick={() => setNoticesSession(!noticesSession)}
              className="group cursor-pointer transition-colors"
            >
              <Bracket className={noticesSession ? "text-status-ok group-hover:text-status-bad" : "text-[#9A968B] group-hover:text-status-ok"}>
                {noticesSession ? "x" : "\u00a0"}
              </Bracket>
            </button>
            <span className="text-[#9A968B]">Session Notifications</span>
          </span>

          <span className="inline-flex items-center gap-0">
            <span className="text-[#9A968B]">{"type: "}</span>
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
            <span className="text-[#9A968B]">{"email: "}</span>
            <span className="text-[#f4f3ee]">{"["}</span>
            <input
              type="email"
              value={notifyEmail}
              onChange={(e) => setNotifyEmail(e.target.value)}
              placeholder="email@example.com"
              style={{ width: "20ch" }}
              className="bg-transparent text-[#f4f3ee] placeholder-[#9A968B] outline-none font-mono min-w-0 px-0"
            />
            <span className="text-[#f4f3ee]">{"]"}</span>
          </span>

          <span className="inline-flex items-center gap-0">
            <span className="text-[#9A968B]">{"phone: "}</span>
            <span className="text-[#f4f3ee]">{"["}</span>
            <input
              type="tel"
              value={formatPhone(notifyPhone)}
              onChange={(e) => setNotifyPhone(stripPhone(e.target.value))}
              placeholder="(123) 456-7890"
              style={{ width: "16ch" }}
              className="bg-transparent text-[#f4f3ee] placeholder-[#9A968B] outline-none font-mono min-w-0 px-0"
            />
            <span className="text-[#f4f3ee]">{"]"}</span>
          </span>
        </div>

        <div className="px-4 py-3 border-t border-[#3d3d3a] flex items-center gap-x-5 gap-y-2 flex-wrap text-sm">
          <span className="inline-flex items-center gap-1">
            <button
              type="button"
              onClick={() => setNoticesLogin(!noticesLogin)}
              className="group cursor-pointer transition-colors"
            >
              <Bracket className={noticesLogin ? "text-status-ok group-hover:text-status-bad" : "text-[#9A968B] group-hover:text-status-ok"}>
                {noticesLogin ? "x" : "\u00a0"}
              </Bracket>
            </button>
            <span className="text-[#9A968B]">Login Issue Notifications</span>
          </span>
        </div>
      </div>

      <div className={sectionCls}>
        <div className="px-4 py-2 border-b border-[#3d3d3a] text-[#9A968B] bg-[#1a1918]">universal ignore</div>

        <div className="px-4 py-3 text-sm">
          <textarea
            value={ignoreHandles}
            onChange={(e) => setIgnoreHandles(e.target.value)}
            placeholder="----"
            rows={3}
            className="w-full bg-transparent text-[#f4f3ee] placeholder-[#9A968B] outline-none font-mono border border-[#3d3d3a] px-2 py-1 focus:border-[#d97757] transition-colors resize-y"
          />
          <span className="text-[#9A968B] text-xs">comma-separated list of accounts to ignore</span>
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
