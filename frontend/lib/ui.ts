export const RISK_STYLE: Record<string, string> = {
  low: "text-ok border-ok/40 bg-ok/10", medium: "text-warn border-warn/40 bg-warn/10", high: "text-bad border-bad/40 bg-bad/10",
};
export const STATUS_STYLE: Record<string, string> = {
  draft: "text-dim border-line bg-white/5", indexing: "text-ind border-ind/40 bg-ind/10", active: "text-ok border-ok/40 bg-ok/10",
  testing: "text-ind border-ind/40 bg-ind/10", approved: "text-cy border-cy/40 bg-cy/10", deployed: "text-cy border-cy/40 bg-cy/10",
  deprecated: "text-faint border-line bg-white/5", archived: "text-faint border-line bg-white/5",
  uploaded: "text-dim border-line bg-white/5", parsed: "text-dim border-line bg-white/5", chunked: "text-ind border-ind/40 bg-ind/10",
  embedded: "text-ind border-ind/40 bg-ind/10", indexed: "text-ok border-ok/40 bg-ok/10", failed: "text-bad border-bad/40 bg-bad/10",
  stale: "text-warn border-warn/40 bg-warn/10", pending_approval: "text-warn border-warn/40 bg-warn/10",
};
export const BADGE_STYLE: Record<string, string> = {
  "Low Risk": RISK_STYLE.low, "Medium Risk": RISK_STYLE.medium, "High Risk": RISK_STYLE.high,
  "PII Risk": "text-bad border-bad/40 bg-bad/10", "Requires Citations": "text-cy border-cy/40 bg-cy/10",
  "Strict Grounding": "text-vi border-vi/40 bg-vi/10", "Stale Content Warning": "text-warn border-warn/40 bg-warn/10",
  "External Source": "text-ind border-ind/40 bg-ind/10", "Tenant Isolated": "text-cy border-cy/40 bg-cy/10",
  "Approval Required": "text-warn border-warn/40 bg-warn/10",
};
export const label = (s: string) => (s || "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
export const RETRIEVAL_MODES = ["hybrid", "semantic", "keyword", "recent", "source", "policy-safe"];
