async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, { ...init, credentials: "include", headers: { "Content-Type": "application/json", ...(init?.headers || {}) } });
  if (!r.ok) {
    let detail = `HTTP ${r.status}`;
    try { detail = (await r.json()).detail || detail; } catch {}
    const e = new Error(detail) as Error & { status?: number }; e.status = r.status; throw e;
  }
  return r.json();
}

export const api = {
  entitlements: () => req<any>("/api/auth/entitlements"),
  stats: () => req<any>("/api/stats"),
  meta: () => req<{ transports: string[]; auth_types: string[]; note: string }>("/api/meta"),

  connectors: () => req<{ connectors: any[] }>("/api/connectors").then((d) => d.connectors),
  connector: (id: string) => req<any>(`/api/connectors/${id}`),
  createConnector: (b: any) => req<any>("/api/connectors", { method: "POST", body: JSON.stringify(b) }).then((d) => d.connector),
  patchConnector: (id: string, b: any) => req<any>(`/api/connectors/${id}`, { method: "PATCH", body: JSON.stringify(b) }).then((d) => d.connector),
  deleteConnector: (id: string) => req<any>(`/api/connectors/${id}`, { method: "DELETE" }),
  discover: (id: string, b: { endpoint_url?: string; auth_value?: string }) => req<any>(`/api/connectors/${id}/discover`, { method: "POST", body: JSON.stringify(b) }),

  versions: (id: string) => req<{ versions: any[] }>(`/api/connectors/${id}/versions`).then((d) => d.versions),
  freezeVersion: (id: string) => req<any>(`/api/connectors/${id}/versions`, { method: "POST", body: "{}" }).then((d) => d.version),

  test: (b: { connector_id: string; tool_name: string; arguments?: any; auth_value?: string; approve?: boolean }) =>
    req<any>("/api/test", { method: "POST", body: JSON.stringify(b) }),
  tests: () => req<{ tests: any[] }>("/api/tests").then((d) => d.tests),
  getTest: (id: string) => req<any>(`/api/tests/${id}`),

  exportUrl: (id: string) => `/api/connectors/${id}/export`,
};

export const ms = (n: number | null | undefined) => (n == null ? "—" : n >= 1000 ? (n / 1000).toFixed(2) + "s" : Math.round(n) + "ms");
export const num = (n: number) => (n ?? 0).toLocaleString();
