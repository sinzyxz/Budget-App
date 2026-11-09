const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const getToken = () => (typeof window === "undefined" ? null : localStorage.getItem("token"));
export const setToken = (t: string | null) =>
  t ? localStorage.setItem("token", t) : localStorage.removeItem("token");

export async function api<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(BASE + path, {
    ...opts,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...opts.headers },
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error(typeof e.detail === "string" ? e.detail : "เกิดข้อผิดพลาด ลองใหม่อีกครั้ง");
  }
  return res.status === 204 ? (undefined as T) : res.json();
}
