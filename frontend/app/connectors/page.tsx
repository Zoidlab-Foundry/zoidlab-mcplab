"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "../../lib/api";

const RISK: Record<string, string> = { high: "bg-bad/10 text-bad", medium: "bg-warn/10 text-warn", low: "bg-ok/10 text-ok" };

export default function ConnectorsPage() {
  const [conns, setConns] = useState<any[]>([]);
  const [meta, setMeta] = useState<any>(null);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [f, setF] = useState<any>({ name: "", description: "", transport: "http", endpoint_url: "", auth_type: "none", auth_ref: "", risk_level: "medium", human_approval: false });

  const load = () => { api.connectors().then(setConns).catch(() => {}); };
  useEffect(() => { load(); api.meta().then(setMeta).catch(() => {}); }, []);
  const set = (k: string, v: any) => setF((p: any) => ({ ...p, [k]: v }));

  async function save() {
    if (!f.name.trim()) return;
    setSaving(true);
    try { await api.createConnector(f); setOpen(false); setF({ name: "", description: "", transport: "http", endpoint_url: "", auth_type: "none", auth_ref: "", risk_level: "medium", human_approval: false }); load(); }
    finally { setSaving(false); }
  }

  return (
    <div className="py-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-semibold">Connectors</h1>
          <p className="mt-1 text-[13px] text-dim">Register an MCP server, then discover, govern, test, and version it. Catalog entries are starting templates — point them at a reachable endpoint to make them real.</p>
        </div>
        <button onClick={() => setOpen(true)} className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-black hover:opacity-90">New connector</button>
      </div>

      <div className="mt-6 grid gap-3 md:grid-cols-2">
        {conns.map((c) => (
          <Link key={c.id} href={`/connectors/${c.id}`} className="rounded-2xl border border-line bg-panel p-4 hover:border-vi/40">
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="text-[14px] font-semibold text-ink">{c.name}{c.catalog && <span className="ml-2 rounded-full bg-panel2 px-1.5 py-0.5 text-[10px] text-faint">catalog</span>}</div>
                <div className="mt-0.5 text-[11px] text-faint">{c.transport} · {c.auth_type} · v{c.version}</div>
              </div>
              <span className={`rounded-full px-2 py-0.5 text-[10.5px] ${RISK[c.risk_level] || "bg-panel2 text-dim"}`}>{c.risk_level}</span>
            </div>
            {c.description && <p className="mt-2 line-clamp-2 text-[12.5px] text-dim">{c.description}</p>}
            <div className="mt-2 flex items-center gap-2 text-[11px] text-faint">
              <span>{(c.tools || []).length} tools</span>
              <span>· {c.status}</span>
              {c.human_approval && <span className="rounded-full bg-warn/10 px-1.5 py-0.5 text-warn">approval required</span>}
            </div>
          </Link>
        ))}
        {!conns.length && <div className="md:col-span-2 rounded-2xl border border-line bg-panel p-8 text-center text-[13px] text-faint">No connectors yet.</div>}
      </div>

      {open && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/60 p-4 backdrop-blur-sm">
          <div className="mt-10 w-full max-w-xl rounded-2xl border border-line bg-panel p-6">
            <div className="flex items-center justify-between">
              <h2 className="text-[16px] font-semibold">New connector</h2>
              <button onClick={() => setOpen(false)} className="text-faint hover:text-ink">✕</button>
            </div>
            <div className="mt-4 grid gap-3">
              <label className="block"><span className="text-[12px] text-dim">Name</span>
                <input value={f.name} onChange={(e) => set("name", e.target.value)} placeholder="e.g. Internal Docs MCP" className={inp} /></label>
              <label className="block"><span className="text-[12px] text-dim">Description</span>
                <input value={f.description} onChange={(e) => set("description", e.target.value)} className={inp} /></label>
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block"><span className="text-[12px] text-dim">Transport</span>
                  <select value={f.transport} onChange={(e) => set("transport", e.target.value)} className={inp}>
                    {(meta?.transports || ["http", "sse", "stdio"]).map((t: string) => <option key={t} value={t}>{t}</option>)}
                  </select></label>
                <label className="block"><span className="text-[12px] text-dim">Risk level</span>
                  <select value={f.risk_level} onChange={(e) => set("risk_level", e.target.value)} className={inp}>
                    {["low", "medium", "high"].map((r) => <option key={r} value={r}>{r}</option>)}
                  </select></label>
              </div>
              <label className="block"><span className="text-[12px] text-dim">Endpoint URL {f.transport === "stdio" ? "(n/a for stdio)" : ""}</span>
                <input value={f.endpoint_url} onChange={(e) => set("endpoint_url", e.target.value)} placeholder="https://mcp.example.com/mcp" className={inp} /></label>
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block"><span className="text-[12px] text-dim">Auth type</span>
                  <select value={f.auth_type} onChange={(e) => set("auth_type", e.target.value)} className={inp}>
                    {(meta?.auth_types || ["none", "bearer", "header"]).map((t: string) => <option key={t} value={t}>{t}</option>)}
                  </select></label>
                <label className="block"><span className="text-[12px] text-dim">Auth reference (label only)</span>
                  <input value={f.auth_ref} onChange={(e) => set("auth_ref", e.target.value)} placeholder="e.g. github_pat" className={inp} /></label>
              </div>
              <label className="flex items-center gap-2 text-[12.5px] text-dim">
                <input type="checkbox" checked={f.human_approval} onChange={(e) => set("human_approval", e.target.checked)} className="accent-vi" />
                Require human approval before any tool call
              </label>
              <p className="text-[11px] text-faint">Secrets are never stored — the auth reference is a label your runtime resolves to a real credential.</p>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button onClick={() => setOpen(false)} className="rounded-lg border border-line px-4 py-2 text-[13px] text-dim hover:text-ink">Cancel</button>
              <button onClick={save} disabled={saving || !f.name.trim()} className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-black hover:opacity-90 disabled:opacity-40">
                {saving ? "Saving…" : "Create connector"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const inp = "mt-1 w-full rounded-lg border border-line bg-panel2 px-3 py-2 text-[13px] text-ink outline-none focus:border-vi/50";
