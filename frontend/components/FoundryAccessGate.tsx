"use client";
// Reusable Foundry Pro gate. Drop it around any Foundry package's content and it
// enforces the Nyquest Pro entitlement client-side (the backend `require_pro`
// dependency and the Next middleware are the other two layers). Exempt routes
// (the gate screen itself + the SSO handoff) always render through.
import { usePathname } from "next/navigation";
import { useAuth } from "../lib/auth";
import ProRequiredScreen from "./ProRequiredScreen";

const EXEMPT = ["/upgrade", "/enter", "/sso"];

export default function FoundryAccessGate({
  children, packageLabel,
}: { children: React.ReactNode; packageLabel?: string }) {
  const pathname = usePathname() || "/";
  const { ent, state, reload } = useAuth();

  if (EXEMPT.some((p) => pathname.startsWith(p))) return <>{children}</>;

  if (state === "loading" && !ent) {
    return <div className="flex min-h-[70vh] items-center justify-center text-[13px] text-dim">Verifying Nyquest Pro access…</div>;
  }
  if (state === "error" || (ent && !ent.foundry_access)) {
    return <ProRequiredScreen ent={ent} state={state} reload={reload} packageLabel={packageLabel} />;
  }
  return <>{children}</>;
}
