"use client";
import { useEffect, useState } from "react";

interface Me { authenticated: boolean; name?: string; email?: string; plan?: string; }

export function useUser() {
  const [user, setUser] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    fetch("/api/auth/me", { credentials: "include" })
      .then((r) => (r.ok ? r.json() : { authenticated: false }))
      .then(setUser).catch(() => setUser({ authenticated: false })).finally(() => setLoading(false));
  }, []);
  return { user, loading, authed: !!user?.authenticated };
}
