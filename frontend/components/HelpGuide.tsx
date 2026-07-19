"use client";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

/* In-app guide: what MCPLab is and how to govern your first connector.
   Auto-opens once per browser (localStorage) and lives behind the Guide nav button. */

const STORAGE_KEY = "mcp_guide_v1";

const STEPS: { title: string; body: string }[] = [
  {
    title: "Register a connector",
    body: "On Connectors, click New Connector — name it, pick a transport (http, sse, or stdio), set the endpoint URL, and choose an auth type. Secrets are never stored: the auth reference is just a label your runtime resolves.",
  },
  {
    title: "Discover its tools",
    body: "Open the connector and hit Discover Tools — MCPLab performs a real MCP handshake against the endpoint and pulls the live tool manifest. stdio connectors can't be reached from the control plane, but you can still govern and version them here.",
  },
  {
    title: "Set the governance rules",
    body: "Allow or block individual tools, set the connector's status and risk level, and flip on human approval to require an explicit sign-off before any tool call runs.",
  },
  {
    title: "Run real test calls",
    body: "Pick a tool, give it JSON arguments, and run a test call. Each call executes as a durable background job against the real server — governance is enforced on the way in, so blocked or approval-gated calls show their decision.",
  },
  {
    title: "Review every call on Tests",
    body: "The Tests page logs every tool invocation and every governance decision — allowed, denied, blocked, or awaiting approval — with status, decision, and measured latency per call.",
  },
  {
    title: "Freeze a version & export",
    body: "Freeze Version snapshots the connector's manifest with an integrity digest, and Export produces a signed Foundry report — evidence you can attach to a review or audit.",
  },
];

export default function HelpGuide() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    try {
      if (!localStorage.getItem(STORAGE_KEY)) setOpen(true);
    } catch {}
  }, []);

  const dismiss = () => {
    try { localStorage.setItem(STORAGE_KEY, "1"); } catch {}
    setOpen(false);
  };

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") dismiss(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="rounded-lg border border-line px-3 py-1.5 text-[12px] text-dim transition hover:text-ink hover:bg-white/5"
        aria-label="Open the MCPLab guide"
      >
        Guide
      </button>
      {open && createPortal(
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={dismiss} role="dialog" aria-modal="true" aria-label="MCPLab guide">
          <div className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-xl border border-line bg-panel p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="mb-1 flex items-center gap-2">
              <span className="grid h-6 w-6 place-items-center rounded-md bg-vi/15 text-[13px] text-vi">⧉</span>
              <h2 className="text-[16px] font-semibold">How MCPLab works</h2>
            </div>
            <p className="mb-5 text-[13px] text-dim">
              Register, govern, test, and version MCP connectors — real handshakes, real tool calls, signed evidence. Six steps from zero to governed:
            </p>
            <ol className="space-y-4">
              {STEPS.map((s, i) => (
                <li key={i} className="flex gap-3">
                  <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-vi/15 text-[12px] font-semibold text-vi">{i + 1}</span>
                  <div>
                    <div className="text-[13.5px] font-medium">{s.title}</div>
                    <div className="text-[12.5px] leading-relaxed text-dim">{s.body}</div>
                  </div>
                </li>
              ))}
            </ol>
            <div className="mt-6 flex items-center justify-between border-t border-line pt-4">
              <a href="https://foundry.zoidlab.ai" className="text-[12px] text-dim hover:text-ink">◈ All Foundry apps</a>
              <button onClick={dismiss} className="rounded-lg bg-vi px-4 py-1.5 text-[12.5px] font-semibold text-black hover:opacity-90">
                Got it
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </>
  );
}
