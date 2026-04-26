"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  createDesktopBuild,
  listDesktopBuilds,
  getDesktopBuild,
  getDesktopBuildDownloadUrl,
  revokeDesktopBuild,
  DesktopBuild,
  DesktopBuildConfig,
  DesktopBuildWithToken,
} from "@/lib/api";
import { Bracket } from "@/lib/bracket";
import { BracketInput } from "@/lib/bracket-input";
import { BracketCheckbox } from "@/lib/bracket-checkbox";

const DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36";

const DEFAULT_CONFIG: DesktopBuildConfig = {
  system_type: "windows",
  chrome_path: "\\PortableChrome\\chrome.exe",
  chrome_version: "143",
  chrome_user_data_dir_base: "\\PortableChrome\\",
  headless: false,
  detach: false,
  close_browser_session: false,
  close_browser_exit: false,
  bot_idle_delay: 5,
  bot_debug: false,
  system_user_agent: DEFAULT_USER_AGENT,
  add_arguments: [],
  api_url: "",
};

const sectionCls = "border border-[#3d3d3a]";

function statusColor(status: string): string {
  if (status === "ready") return "text-status-ok";
  if (status === "failed" || status === "revoked") return "text-status-bad";
  return "text-[#E5C07B]";
}

function isActive(b: DesktopBuild) { return b.status === "queued" || b.status === "running"; }
function isExpired(b: DesktopBuild) { return new Date(b.download_expires_at) < new Date(); }

function configSummary(cfg: DesktopBuildConfig): string {
  const parts: string[] = [];
  if (cfg.headless) parts.push("headless");
  if (cfg.chrome_path.toLowerCase().includes("portable")) parts.push("portable chrome");
  if (cfg.bot_debug) parts.push("debug");
  return parts.length ? parts.join(", ") : "default";
}


export default function ClientPage() {
  const [builds, setBuilds] = useState<DesktopBuild[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [config, setConfig] = useState<DesktopBuildConfig>(DEFAULT_CONFIG);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [justCreated, setJustCreated] = useState<DesktopBuildWithToken | null>(null);
  const [copied, setCopied] = useState(false);
  const [revoking, setRevoking] = useState<string | null>(null);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const nextClientId = useMemo(() => {
    if (builds.length === 0) return 1;
    const max = Math.max(...builds.map((b) => b.client_id));
    return max >= 99 ? 1 : max + 1;
  }, [builds]);

  async function load() {
    try {
      const data = await listDesktopBuilds();
      setBuilds(data);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load builds.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  useEffect(() => {
    const active = builds.filter(isActive);
    if (active.length === 0) { if (pollRef.current) clearInterval(pollRef.current); return; }
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      const updated = await Promise.all(active.map((b) => getDesktopBuild(b.id).catch(() => b)));
      setBuilds((prev) => prev.map((b) => updated.find((u) => u.id === b.id) ?? b));
    }, 10_000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [builds]);

  function setField<K extends keyof DesktopBuildConfig>(key: K, value: DesktopBuildConfig[K]) {
    setConfig((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit() {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const result = await createDesktopBuild(config);
      setJustCreated(result);
      setConfig(DEFAULT_CONFIG);
      await load();
    } catch (e: unknown) {
      setSubmitError(e instanceof Error ? e.message : "Build request failed.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRevoke(buildId: string) {
    if (!confirm("Revoke this build? The EXE will no longer be downloadable.")) return;
    setRevoking(buildId);
    try {
      const updated = await revokeDesktopBuild(buildId);
      setBuilds((prev) => prev.map((b) => (b.id === buildId ? updated : b)));
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Revoke failed.");
    } finally {
      setRevoking(null);
    }
  }

  function handleDownload(buildId: string) {
    const token = localStorage.getItem("token");
    const url = getDesktopBuildDownloadUrl(buildId);
    fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then(async (res) => {
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body?.detail ?? `Download failed: ${res.status}`);
        }
        const blob = await res.blob();
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        const build = builds.find((b) => b.id === buildId);
        a.download = `SlowBurnBot-client${build?.client_id ?? ""}.exe`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(a.href);
        await load();
      })
      .catch((e) => alert(e.message));
  }

  function copyToken(token: string) {
    navigator.clipboard.writeText(token).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="space-y-4 font-mono">
      <h1 className="font-semibold text-[#f4f3ee]">Client</h1>

      {justCreated && (
        <div className="border border-[#d97757] px-4 py-4 space-y-2">
          <div className="text-[#f4f3ee]">
            Build requested — <span className="text-status-ok">client {justCreated.client_id}</span> queued.
          </div>
          <div className="text-[#9A968B] text-sm">Activation token (shown once — copy it now):</div>
          <div className="flex items-center gap-3 flex-wrap">
            <code className="text-[#E5C07B] break-all text-xs">{justCreated.activation_token}</code>
            <button onClick={() => copyToken(justCreated.activation_token)} className="text-[#9A968B] hover:text-[#f4f3ee] transition-colors text-xs">
              <Bracket>{copied ? "copied!" : "copy"}</Bracket>
            </button>
            <button onClick={() => setJustCreated(null)} className="text-[#9A968B] hover:text-[#f4f3ee] transition-colors text-xs ml-auto">
              <Bracket>dismiss</Bracket>
            </button>
          </div>
        </div>
      )}

      {/* Build history */}
      <div className={sectionCls}>
        <div className="px-4 py-2 border-b border-[#3d3d3a] bg-[#1a1918]">
          <span className="text-[#f4f3ee]">builds</span>
        </div>

        {loading && <div className="px-4 py-4 text-[#9A968B]">loading...</div>}
        {!loading && error && <div className="px-4 py-4 text-status-bad">{error}</div>}
        {!loading && !error && builds.length === 0 && <div className="px-4 py-4 text-[#9A968B]">No builds yet.</div>}

        {!loading && !error && builds.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-[#9A968B] border-b border-[#3d3d3a] bg-[#1a1918]">
                  <th className="px-4 py-2 font-normal">requested</th>
                  <th className="px-4 py-2 font-normal">client</th>
                  <th className="px-4 py-2 font-normal">status</th>
                  <th className="px-4 py-2 font-normal">config</th>
                  <th className="px-4 py-2 font-normal">downloads</th>
                  <th className="px-4 py-2 font-normal"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#3d3d3a]">
                {builds.map((build) => {
                  const canDownload = build.status === "ready" && !isExpired(build) && build.download_count < build.max_downloads;
                  const expired = build.status === "ready" && isExpired(build);
                  const cfg = build.build_options as DesktopBuildConfig;
                  return (
                    <tr key={build.id} className="hover:bg-[#1f1e1d] transition-colors">
                      <td className="px-4 py-3 text-[#9A968B] text-sm whitespace-nowrap">
                        {new Date(build.created_at).toLocaleDateString()}{" "}
                        {new Date(build.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </td>
                      <td className="px-4 py-3 text-[#f4f3ee]">#{build.client_id}</td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className={statusColor(build.status)}>{build.status}</span>
                      </td>
                      <td className="px-4 py-3 text-[#9A968B] text-xs">{configSummary(cfg)}</td>
                      <td className="px-4 py-3 text-[#9A968B] text-sm">
                        {build.status === "ready" ? (
                          expired ? <span className="text-status-bad">expired</span> : <span>{build.download_count}/{build.max_downloads}</span>
                        ) : <span>----</span>}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex gap-2 justify-end">
                          {canDownload && (
                            <button onClick={() => handleDownload(build.id)} className="text-[#9A968B] hover:text-[#f4f3ee] transition-colors text-sm">
                              <Bracket>download</Bracket>
                            </button>
                          )}
                          {build.status !== "revoked" && build.status !== "failed" && (
                            <button onClick={() => handleRevoke(build.id)} disabled={revoking === build.id} className="text-[#9A968B] hover:text-status-bad transition-colors text-sm disabled:text-[#3d3d3a]">
                              <Bracket>{revoking === build.id ? "…" : "revoke"}</Bracket>
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Generate new client */}
      <div className={sectionCls}>
        <div className="px-4 py-2 border-b border-[#3d3d3a] bg-[#1a1918]">
          <span className="text-[#f4f3ee]">
            generate new client
            <span className="text-[#9A968B] ml-2">
              -- client id: <span className="text-[#f4f3ee]">[</span><span className="text-[#E5C07B]">{String(nextClientId).padStart(2, "0")}</span><span className="text-[#f4f3ee]">]</span>
            </span>
          </span>
        </div>

        <div className="px-4 py-3 flex flex-col gap-y-3 text-sm">

          {/* Portable chrome version + user agent */}
          <div className="flex items-center gap-x-0 gap-y-2 flex-wrap">
            <BracketInput label="portable chrome version" value={config.chrome_version} onChange={(v) => setField("chrome_version", v)} width="5ch" placeholder="143" />
            <BracketInput label="user agent" value={config.system_user_agent} onChange={(v) => setField("system_user_agent", v)} width="52ch" />
          </div>

          {/* Chrome path + user data dir */}
          <div className="flex items-center gap-x-0 gap-y-2 flex-wrap">
            <BracketInput label="chrome path" value={config.chrome_path} onChange={(v) => setField("chrome_path", v)} width="36ch" placeholder="\PortableChrome\chrome.exe" />
            <BracketInput label="user data dir" value={config.chrome_user_data_dir_base} onChange={(v) => setField("chrome_user_data_dir_base", v)} width="24ch" placeholder="\PortableChrome\" />
          </div>

          {/* Headless + detach + close on session end + close on exit */}
          <div className="flex items-center gap-x-5 gap-y-2 flex-wrap">
            <BracketCheckbox label="headless" checked={config.headless} onChange={(v) => setField("headless", v)} />
            <BracketCheckbox label="detach" checked={config.detach} onChange={(v) => setField("detach", v)} />
            <BracketCheckbox label="close on session end" checked={config.close_browser_session} onChange={(v) => setField("close_browser_session", v)} />
            <BracketCheckbox label="close on exit" checked={config.close_browser_exit} onChange={(v) => setField("close_browser_exit", v)} />
          </div>

        </div>
      </div>

      <div className="flex items-center gap-3 font-mono text-sm">
        <button
          onClick={handleSubmit}
          disabled={submitting || !config.chrome_path.trim()}
          className="group disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          <Bracket className="text-[#d97757] group-hover:text-[#f4f3ee]">
            {submitting ? "requesting…" : "request build"}
          </Bracket>
        </button>
        <span className="text-[#9A968B] text-xs">Build takes ~5–10 min.</span>
        {submitError && <span className="text-status-bad">{submitError}</span>}
      </div>

      {/* Getting started */}
      <div className={sectionCls}>
        <div className="px-4 py-2 border-b border-[#3d3d3a] bg-[#1a1918]">
          <span className="text-[#f4f3ee]">getting started</span>
        </div>
        <div className="px-4 py-4 space-y-2 text-sm text-[#9A968B]">
          <p><span className="text-[#f4f3ee]">1.</span> Download <code className="text-[#E5C07B]">SlowBurnBot.exe</code> when your build is ready.</p>
          <p><span className="text-[#f4f3ee]">2.</span> Run the EXE on Windows and log in with your dashboard credentials.</p>
          <p><span className="text-[#f4f3ee]">3.</span> The client activates on first launch and runs normally from there.</p>
        </div>
      </div>
    </div>
  );
}
