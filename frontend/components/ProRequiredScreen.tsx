"use client";
// Reusable 3-state Foundry gate screen: not-signed-in / not-Pro / verify-error.
// Used by both the standalone /upgrade route and the <FoundryAccessGate> wrapper,
// so every Foundry package renders an identical, on-brand upgrade experience.
import type { Entitlement } from "../lib/subscription";
import { UPGRADE_URL, BILLING_URL, NYQUEST_URL } from "../lib/subscription";

function Btn({ href, children, solid, onClick }: { href?: string; children: React.ReactNode; solid?: boolean; onClick?: () => void }) {
  const cls = `rounded-lg px-5 py-2.5 text-[13px] font-semibold ${solid ? "bg-vi text-white hover:opacity-90" : "border border-line text-ink hover:bg-white/5"}`;
  return onClick ? <button onClick={onClick} className={cls}>{children}</button> : <a href={href} className={cls}>{children}</a>;
}

export default function ProRequiredScreen({
  ent, state, reload, packageLabel = "Foundry Package 05",
}: { ent: Entitlement | null; state: "loading" | "ok" | "error"; reload: () => void; packageLabel?: string }) {
  let mode: "signin" | "pro" | "error" = "error";
  if (state === "ok" && ent) {
    if (ent.subscription_status === "unauthenticated") mode = "signin";
    else if (!ent.foundry_access) mode = "pro";
    else mode = "signin";
  } else if (state === "error") mode = "error";

  return (
    <div className="flex min-h-[70vh] w-full items-center justify-center px-5 text-center">
      <div className="max-w-md">
        <img src="/logo.svg" alt="" className="mx-auto mb-5 h-14 w-14" />
        <div className="mb-4 flex items-center justify-center gap-2">
          <span className="rounded-full border border-vi/40 bg-vi/10 px-2 py-0.5 text-[10px] font-medium text-vi">{packageLabel}</span>
          <span className="rounded-full border border-line px-2 py-0.5 text-[10px] text-dim">Nyquest Pro</span>
        </div>

        {state === "loading" && <p className="text-[13px] text-dim">Checking your Nyquest subscription…</p>}

        {state !== "loading" && mode === "signin" && (
          <>
            <h1 className="mb-2 text-[22px] font-semibold text-ink">Sign in to Nyquest</h1>
            <p className="mb-6 text-[14px] leading-relaxed text-dim">Access to ZoidLab Foundry requires a Nyquest account. Open ZoidLab from your Nyquest app to sign in.</p>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <Btn href={NYQUEST_URL} solid>Sign in with Nyquest</Btn>
              <Btn href="https://nyquest.ai">Back to Nyquest.ai</Btn>
            </div>
          </>
        )}

        {state !== "loading" && mode === "pro" && (
          <>
            <h1 className="mb-2 text-[22px] font-semibold text-ink">Nyquest Pro Required</h1>
            <p className="mb-6 text-[14px] leading-relaxed text-dim">
              ZoidLab Foundry packages are available to <span className="text-ink">Nyquest Pro</span> subscribers.
              {ent?.plan && <> Your plan is <span className="text-ink">{ent.plan}</span> ({ent.subscription_status}).</>}
            </p>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <Btn href={UPGRADE_URL} solid>Upgrade to Pro</Btn>
              <Btn href={BILLING_URL}>Manage Subscription</Btn>
              <Btn href="https://foundry.zoidlab.ai">Back to Foundry</Btn>
            </div>
          </>
        )}

        {state !== "loading" && mode === "error" && (
          <>
            <h1 className="mb-2 text-[22px] font-semibold text-ink">Unable to verify subscription</h1>
            <p className="mb-6 text-[14px] leading-relaxed text-dim">We could not verify your Nyquest subscription. Try again, or contact support.</p>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <Btn onClick={reload} solid>Retry</Btn>
              <Btn href="https://nyquest.ai/support">Contact Support</Btn>
              <Btn href="https://nyquest.ai">Back to Nyquest.ai</Btn>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
