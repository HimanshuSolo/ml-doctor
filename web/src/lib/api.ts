// API base for the MLDoctor backend. NEXT_PUBLIC_API_BASE always wins. Left
// unset: `next dev` on port 3000 defaults to http://127.0.0.1:8765 (and needs
// MLDOCTOR_DEV_CORS=1 on the backend), and anywhere else the page calls the
// same origin it was served from (one-process fallback, on any port). No
// secrets: the token comes from ?token=/sessionStorage, never from this var.
export function resolveApiBase(envBase: string | undefined, pagePort: string): string {
  if (envBase) return envBase.replace(/\/$/, "");
  return pagePort === "3000" ? "http://127.0.0.1:8765" : "";
}
export const API_BASE = resolveApiBase(
  process.env.NEXT_PUBLIC_API_BASE,
  typeof window !== "undefined" ? window.location.port : "",
);
export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}
