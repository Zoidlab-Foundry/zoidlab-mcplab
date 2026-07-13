"use client";
// Frontend auth + Foundry entitlement helpers. The session cookie is set by the
// shared ZoidLab SSO handoff; this reads the resulting user + entitlement from the
// RAG backend. Entitlement is cached in-memory so the reusable <FoundryAccessGate>
// doesn't re-fetch on every navigation.
import { useEffect, useState } from "react";
import type { Entitlement } from "./subscription";

export interface Me {
  user_id: string | null;
  email: string | null;
  name?: string | null;
  tier?: string | null;
  authenticated: boolean;
}

let _entPromise: Promise<Entitlement> | null = null;
let _entCache: Entitlement | null = null;

export async function getEntitlement(force = false): Promise<Entitlement> {
  if (_entCache && !force) return _entCache;
  if (_entPromise && !force) return _entPromise;
  _entPromise = fetch("/api/auth/entitlements", { credentials: "include" })
    .then((r) => { if (!r.ok) throw new Error("entitlement_fetch_failed"); return r.json(); })
    .then((e: Entitlement) => { _entCache = e; return e; })
    .finally(() => { _entPromise = null; });
  return _entPromise;
}

export function clearEntitlementCache() { _entCache = null; _entPromise = null; }

export async function getMe(): Promise<Me> {
  const r = await fetch("/api/auth/me", { credentials: "include" });
  if (!r.ok) return { user_id: null, email: null, authenticated: false };
  return r.json();
}

/** Reusable auth hook: entitlement + loading/error state, with a manual reload. */
export function useAuth() {
  const [ent, setEnt] = useState<Entitlement | null>(_entCache);
  const [state, setState] = useState<"loading" | "ok" | "error">(_entCache ? "ok" : "loading");
  const load = (force = false) => {
    setState(_entCache && !force ? "ok" : "loading");
    getEntitlement(force).then((e) => { setEnt(e); setState("ok"); }).catch(() => setState("error"));
  };
  useEffect(() => { load(); }, []);
  return { ent, state, reload: () => load(true) };
}
