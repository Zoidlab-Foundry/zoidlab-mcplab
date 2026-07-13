"use client";
import { useEffect, useState } from "react";

export interface Entitlement {
  user_id: string | null; email: string | null; name?: string;
  plan: string | null; subscription_status: string;
  foundry_access: boolean; allowed_packages: string[]; reason?: string | null; mock?: boolean;
}

export const UPGRADE_URL = "https://app.nyquest.ai/pricing";
export const BILLING_URL = "https://app.nyquest.ai/billing";
export const NYQUEST_URL = "https://app.nyquest.ai";

export function useEntitlement() {
  const [ent, setEnt] = useState<Entitlement | null>(null);
  const [state, setState] = useState<"loading" | "ok" | "error">("loading");
  const load = () => {
    setState("loading");
    fetch("/api/auth/entitlements", { credentials: "include" })
      .then((r) => { if (!r.ok) throw new Error(); return r.json(); })
      .then((e) => { setEnt(e); setState("ok"); })
      .catch(() => setState("error"));
  };
  useEffect(load, []);
  return { ent, state, reload: load };
}
