"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, num } from "../lib/api";

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-2xl border border-line bg-panel p-4">
      <div className="text-[11px] uppercase tracking-wider text-faint">{label}</div>
      <div className="mt-1.5 text-[24px] font-semibold tnum text-ink">{value}</div>
      {sub && <div className="mt-0.5 text-[12px] text-dim">{sub}</div>}
    </div>
  );
}

const RISK: Record<string, string> = { high: "bg-bad/10 text-bad", medium: "bg-warn/10 text-warn", low: "bg-ok/10 text-ok" };

export default function Dashboard() {
  const [s, setS] = useState<any>(null);
  const [conns, setConns] = useState<any[]>([]);
  const [tests, setTests] = useState<any[]>([]);

  useEffect(() => {
    api.stats().then(setS).catch(() => {});
    api.connectors().then(setConns).catch(() => {});
    api.tests().then((t) => setTests(t.slice(0, 6))).catch(() => {});
  }, []);

  return (
    <div className="relative py-8">
      <div className="hero-glow" />
      <div className="relative flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[26px] font-semibold tracking-tight">
            Every connector, <span className="prism-text">governed</span>.
          </h1>
          <p className="mt-1.5 max-w-2xl text-[13px] leading-relaxed text-dim">
            A control plane for Model Context Protocol connectors: register them, discover their tools with a
            real MCP handshake, gate which tools are callable, test-call them for real over HTTP, and freeze
            immutable, integrity-hashed versions.
          </p>
        </div>
        <Link href="/connectors" className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-black hover:opacity-90">
          Manage connectors →
        </Link>
      </div>

      <div className="relative mt-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Connectors" value={num(s?.connectors ?? 0)} sub={`${num(s?.active ?? 0)} active`} />
        <Stat label="Discovered tools" value={num(s?.tools ?? 0)} sub="across connectors" />
        <Stat label="Test calls" value={num(s?.tests ?? 0)} sub="real MCP invocations" />
        <Stat label="Active" value={num(s?.active ?? 0)} sub="in production use" />
      </div>

      <div className="relative mt-4 grid gap-4 lg:grid-cols-[1.2fr_1fr]">
        <div className="rounded-2xl border border-line bg-panel p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-[14px] font-semibold">Connectors</h2>
            <Link href="/connectors" className="text-[12px] text-cy hover:underline">All →</Link>
          </div>
          <div className="mt-3 space-y-2">
            {conns.slice(0, 7).map((c) => (
              <Link key={c.id} href={`/connectors/${c.id}`} className="block rounded-lg border border-line bg-panel2 p-2.5 hover:border-vi/40">
                <div className="flex items-center justify-between">
                  <div className="text-[12.5px] font-medium text-ink">{c.name}</div>
                  <div className="flex items-center gap-1.5">
                    <span className="rounded-full bg-panel px-2 py-0.5 text-[10px] text-dim">{c.transport}</span>
                    <span className={`rounded-full px-2 py-0.5 text-[10px] ${RISK[c.risk_level] || "bg-panel text-dim"}`}>{c.risk_level}</span>
                  </div>
                </div>
                <div className="mt-0.5 text-[11px] text-faint">{(c.tools || []).length} tools · {c.status}{c.catalog ? " · catalog" : ""}</div>
              </Link>
            ))}
            {!conns.length && <p className="text-[12px] text-faint">No connectors yet.</p>}
          </div>
        </div>
        <div className="rounded-2xl border border-line bg-panel p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-[14px] font-semibold">Recent tests</h2>
            <Link href="/tests" className="text-[12px] text-cy hover:underline">All →</Link>
          </div>
          <div className="mt-3 space-y-2">
            {tests.map((t) => (
              <div key={t.id} className="rounded-lg border border-line bg-panel2 p-2.5">
                <div className="flex items-center justify-between">
                  <div className="text-[12.5px] font-medium text-ink">{t.connector_name}</div>
                  <span className={`rounded-full px-2 py-0.5 text-[10.5px] ${t.status === "completed" && !t.is_error ? "bg-ok/10 text-ok" : t.status === "blocked" ? "bg-warn/10 text-warn" : "bg-bad/10 text-bad"}`}>{t.status}</span>
                </div>
                <div className="mt-0.5 text-[11px] text-faint">{t.tool_name} · {t.decision || "—"}</div>
              </div>
            ))}
            {!tests.length && <p className="text-[12px] text-faint">No test calls yet.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
