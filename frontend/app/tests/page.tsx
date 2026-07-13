"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, ms } from "../../lib/api";

function statusStyle(t: any) {
  if (t.status === "completed" && !t.is_error) return "bg-ok/10 text-ok";
  if (t.status === "blocked") return "bg-warn/10 text-warn";
  return "bg-bad/10 text-bad";
}

export default function TestsPage() {
  const [tests, setTests] = useState<any[]>([]);
  useEffect(() => { api.tests().then(setTests).catch(() => {}); }, []);

  return (
    <div className="py-8">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-[22px] font-semibold">Test calls</h1>
          <p className="mt-1 text-[13px] text-dim">Every real tool invocation and every governance decision — allowed, denied, blocked, or requiring approval.</p>
        </div>
        <Link href="/connectors" className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-black hover:opacity-90">Connectors →</Link>
      </div>

      <div className="mt-5 overflow-x-auto rounded-2xl border border-line bg-panel">
        <table className="w-full text-[12.5px]">
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-wider text-faint">
              <th className="px-4 py-3 font-medium">Connector</th>
              <th className="px-4 py-3 font-medium">Tool</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Decision</th>
              <th className="px-4 py-3 font-medium">Latency</th>
              <th className="px-4 py-3 font-medium">When</th>
            </tr>
          </thead>
          <tbody>
            {tests.map((t) => (
              <tr key={t.id} className="border-t border-line/60 hover:bg-panel2/50">
                <td className="px-4 py-3"><Link href={`/connectors/${t.connector_id}`} className="font-medium text-ink hover:text-cy">{t.connector_name}</Link></td>
                <td className="px-4 py-3 font-mono text-[11.5px] text-dim">{t.tool_name}</td>
                <td className="px-4 py-3"><span className={`rounded-full px-2 py-0.5 text-[10.5px] ${statusStyle(t)}`}>{t.is_error ? "tool_error" : t.status}</span></td>
                <td className="px-4 py-3 text-dim">{t.decision || "—"}</td>
                <td className="px-4 py-3 tnum text-dim">{ms(t.latency_ms)}</td>
                <td className="px-4 py-3 text-faint">{t.created_at?.slice(0, 19).replace("T", " ")}</td>
              </tr>
            ))}
            {!tests.length && <tr><td colSpan={6} className="px-4 py-10 text-center text-[13px] text-faint">No test calls yet. <Link href="/connectors" className="text-cy hover:underline">Test a connector</Link>.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
