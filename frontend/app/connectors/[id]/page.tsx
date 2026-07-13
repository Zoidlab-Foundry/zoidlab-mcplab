"use client";
import { use, useEffect, useState } from "react";
import Link from "next/link";
import { api, ms, runToCompletion } from "../../../lib/api";

export default function ConnectorDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [c, setC] = useState<any>(null);
  const [versions, setVersions] = useState<any[]>([]);
  const [authValue, setAuthValue] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [discoverMsg, setDiscoverMsg] = useState<any>(null);
  const [testTool, setTestTool] = useState<string>("");
  const [testArgs, setTestArgs] = useState("{}");
  const [testResult, setTestResult] = useState<any>(null);
  const [err, setErr] = useState(false);

  const load = () => {
    api.connector(id).then((x) => { setC(x); setTestTool((x.tools?.[0]?.name) || ""); }).catch(() => setErr(true));
    api.versions(id).then(setVersions).catch(() => {});
  };
  useEffect(load, [id]);

  if (err) return <div className="py-10 text-[13px] text-faint">Connector not found. <Link href="/connectors" className="text-cy hover:underline">Back</Link>.</div>;
  if (!c) return <div className="py-10 text-[13px] text-dim">Loading…</div>;

  async function discover() {
    setBusy("discover"); setDiscoverMsg(null);
    try {
      const r = await api.discover(id, { auth_value: authValue || undefined });
      setDiscoverMsg(r); load();
    } catch (e: any) { setDiscoverMsg({ ok: false, error: e.message }); }
    finally { setBusy(null); }
  }

  async function freeze() {
    setBusy("freeze");
    try { await api.freezeVersion(id); load(); } finally { setBusy(null); }
  }

  async function toggleAllowed(tool: string) {
    const cur = c.allowed_tools || [];
    const next = cur.includes(tool) ? cur.filter((t: string) => t !== tool) : [...cur, tool];
    await api.patchConnector(id, { allowed_tools: next }).catch(() => {});
    load();
  }

  async function setStatus(status: string) { await api.patchConnector(id, { status }).catch(() => {}); load(); }
  async function toggleApproval() { await api.patchConnector(id, { human_approval: !c.human_approval }).catch(() => {}); load(); }

  async function runTest(approve = false) {
    setBusy("test"); setTestResult(null);
    let args = {};
    try { args = JSON.parse(testArgs || "{}"); } catch { setTestResult({ status: "failed", error: "arguments must be valid JSON" }); setBusy(null); return; }
    try {
      const r = await runToCompletion(
        () => api.test({ connector_id: id, tool_name: testTool, arguments: args, auth_value: authValue || undefined, approve }),
        (rid) => api.getTest(rid),
      );
      setTestResult(r); load();
    } catch (e: any) { setTestResult({ status: "failed", error: e.message }); }
    finally { setBusy(null); }
  }

  const httpish = c.transport === "http" || c.transport === "sse";

  return (
    <div className="py-8">
      <Link href="/connectors" className="text-[12px] text-dim hover:text-ink">← Connectors</Link>
      <div className="mt-2 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-semibold">{c.name}</h1>
          <div className="mt-1 text-[12px] text-faint">{c.transport} · {c.auth_type} · v{c.version} {c.catalog && "· catalog template"}</div>
          {c.description && <p className="mt-1 text-[13px] text-dim">{c.description}</p>}
        </div>
        <div className="flex items-center gap-2">
          <a href={api.exportUrl(id)} target="_blank" className="rounded-lg border border-line px-3 py-1.5 text-[12px] text-dim hover:text-ink">Export</a>
          <button onClick={freeze} disabled={busy === "freeze"} className="rounded-lg bg-vi px-3 py-1.5 text-[12px] font-semibold text-black hover:opacity-90 disabled:opacity-40">
            {busy === "freeze" ? "Freezing…" : "Freeze version"}
          </button>
        </div>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-[1.3fr_1fr]">
        <div className="space-y-4">
          {/* discovery */}
          <div className="rounded-2xl border border-line bg-panel p-5">
            <div className="flex items-center justify-between">
              <h2 className="text-[14px] font-semibold">Discovery</h2>
              <span className="text-[11px] text-faint">{c.endpoint_url || "no endpoint set"}</span>
            </div>
            {!httpish && <p className="mt-2 text-[12.5px] text-warn">{c.transport} transport can’t be reached from the control plane — govern & version it here, run it in your own runtime.</p>}
            {httpish && (
              <div className="mt-3 flex flex-wrap items-center gap-2">
                {c.auth_type !== "none" && (
                  <input value={authValue} onChange={(e) => setAuthValue(e.target.value)} type="password" placeholder={`${c.auth_type} value (used now, never stored)`}
                    className="flex-1 rounded-lg border border-line bg-panel2 px-3 py-1.5 text-[12.5px] text-ink outline-none focus:border-vi/50" />
                )}
                <button onClick={discover} disabled={busy === "discover" || !c.endpoint_url} className="rounded-lg bg-vi px-3 py-1.5 text-[12.5px] font-semibold text-black hover:opacity-90 disabled:opacity-40">
                  {busy === "discover" ? "Handshaking…" : "Discover tools"}
                </button>
              </div>
            )}
            {discoverMsg && (
              <div className={`mt-3 rounded-lg border px-3 py-2 text-[12px] ${discoverMsg.ok ? "border-ok/30 bg-ok/5 text-ok" : "border-bad/30 bg-bad/5 text-bad"}`}>
                {discoverMsg.ok ? `Discovered ${discoverMsg.tools?.length ?? 0} tools in ${ms(discoverMsg.latency_ms)}.` : `Discovery failed: ${discoverMsg.error}${discoverMsg.detail ? " — " + discoverMsg.detail : ""}`}
              </div>
            )}
          </div>

          {/* tools + test */}
          <div className="rounded-2xl border border-line bg-panel p-5">
            <h2 className="text-[14px] font-semibold">Tools & governance</h2>
            {!(c.tools || []).length && <p className="mt-2 text-[12.5px] text-faint">No tools discovered yet.</p>}
            <div className="mt-3 space-y-2">
              {(c.tools || []).map((t: any) => {
                const allowed = !(c.allowed_tools || []).length || (c.allowed_tools || []).includes(t.name);
                return (
                  <div key={t.name} className="rounded-lg border border-line bg-panel2 p-2.5">
                    <div className="flex items-center justify-between gap-2">
                      <div>
                        <button onClick={() => setTestTool(t.name)} className={`text-[12.5px] font-medium ${testTool === t.name ? "text-vi" : "text-ink"} hover:text-vi`}>{t.name}</button>
                        {t.description && <div className="text-[11px] text-faint">{t.description}</div>}
                      </div>
                      <button onClick={() => toggleAllowed(t.name)}
                        className={`rounded-full px-2 py-0.5 text-[10.5px] ${allowed ? "bg-ok/10 text-ok" : "bg-bad/10 text-bad"}`}>
                        {(c.allowed_tools || []).length ? (allowed ? "allowed" : "blocked") : "allowed (all)"}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
            {httpish && (c.tools || []).length > 0 && (
              <div className="mt-4 rounded-lg border border-line bg-panel2 p-3">
                <div className="text-[12px] text-dim">Test call — <span className="text-ink">{testTool || "select a tool"}</span></div>
                <textarea value={testArgs} onChange={(e) => setTestArgs(e.target.value)} rows={2} placeholder='{"arg": "value"}'
                  className="mt-2 w-full rounded-lg border border-line bg-panel px-3 py-2 font-mono text-[12px] text-ink outline-none focus:border-vi/50" />
                <div className="mt-2 flex items-center gap-2">
                  <button onClick={() => runTest(false)} disabled={busy === "test" || !testTool} className="rounded-lg bg-vi px-3 py-1.5 text-[12px] font-semibold text-black hover:opacity-90 disabled:opacity-40">
                    {busy === "test" ? "Calling…" : "Run test call"}
                  </button>
                  {c.human_approval && <button onClick={() => runTest(true)} disabled={busy === "test" || !testTool} className="rounded-lg border border-warn/40 px-3 py-1.5 text-[12px] text-warn hover:bg-warn/5">Approve & run</button>}
                </div>
                {testResult && (
                  <div className={`mt-3 rounded-lg border px-3 py-2 text-[12px] ${testResult.status === "completed" && !testResult.is_error ? "border-ok/30 bg-ok/5" : testResult.status === "blocked" ? "border-warn/30 bg-warn/5" : "border-bad/30 bg-bad/5"}`}>
                    <div className="text-dim">status <span className="text-ink">{testResult.status}</span> · decision <span className="text-ink">{testResult.decision || "—"}</span></div>
                    {testResult.error && <div className="mt-1 text-bad">{testResult.error}</div>}
                    {testResult.result && <pre className="mt-1 max-h-48 overflow-auto whitespace-pre-wrap break-words text-[11px] text-ink">{JSON.stringify(testResult.result, null, 2)}</pre>}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* right rail: governance + versions */}
        <div className="space-y-4">
          <div className="rounded-2xl border border-line bg-panel p-5">
            <h2 className="text-[14px] font-semibold">Governance</h2>
            <div className="mt-3 space-y-3 text-[12.5px]">
              <div className="flex items-center justify-between">
                <span className="text-dim">Status</span>
                <select value={c.status} onChange={(e) => setStatus(e.target.value)} className="rounded-lg border border-line bg-panel2 px-2 py-1 text-[12px] text-ink">
                  {["draft", "active", "deprecated"].map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-dim">Risk level</span>
                <span className={`rounded-full px-2 py-0.5 text-[11px] ${c.risk_level === "high" ? "bg-bad/10 text-bad" : c.risk_level === "low" ? "bg-ok/10 text-ok" : "bg-warn/10 text-warn"}`}>{c.risk_level}</span>
              </div>
              <label className="flex items-center justify-between">
                <span className="text-dim">Human approval to call</span>
                <input type="checkbox" checked={c.human_approval} onChange={toggleApproval} className="accent-vi" />
              </label>
              <div className="flex items-center justify-between">
                <span className="text-dim">Allowed tools</span>
                <span className="text-ink">{(c.allowed_tools || []).length || "all"}</span>
              </div>
              {c.auth_ref && <div className="flex items-center justify-between"><span className="text-dim">Auth reference</span><span className="font-mono text-[11px] text-ink">{c.auth_ref}</span></div>}
            </div>
          </div>

          <div className="rounded-2xl border border-line bg-panel p-5">
            <h2 className="text-[14px] font-semibold">Versions</h2>
            <div className="mt-3 space-y-2">
              {versions.map((v) => (
                <div key={v.id} className="rounded-lg border border-line bg-panel2 p-2.5 text-[12px]">
                  <div className="flex items-center justify-between"><span className="font-medium text-ink">v{v.version}</span><span className="text-faint">{v.created_at?.slice(0, 10)}</span></div>
                  <div className="mt-0.5 truncate font-mono text-[10.5px] text-faint" title={v.integrity}>{v.integrity}</div>
                </div>
              ))}
              {!versions.length && <p className="text-[12px] text-faint">No frozen versions yet.</p>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
