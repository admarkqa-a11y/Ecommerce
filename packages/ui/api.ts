let csrf = "";
let csrfRequest: Promise<string> | null = null;
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public data: unknown,
  ) {
    super(message);
  }
}
function describe(data: any): string {
  if (typeof data === "string") return data;
  if (Array.isArray(data)) return data.map(describe).join(" · ");
  if (data && typeof data === "object")
    return Object.entries(data)
      .map(([k, v]) => `${k === "detail" ? "" : k + ": "}${describe(v)}`)
      .join("\n");
  return String(data ?? "Request failed");
}
async function token() {
  if (!csrfRequest)
    csrfRequest = fetch("/api/v1/auth/csrf", {
      credentials: "include",
      cache: "no-store",
    })
      .then(async (r) => {
        if (!r.ok)
          throw new ApiError(
            "Could not establish a secure session.",
            r.status,
            null,
          );
        csrf = (await r.json()).csrfToken;
        return csrf;
      })
      .finally(() => {
        csrfRequest = null;
      });
  return csrfRequest;
}
export async function api<T = any>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const method = (options.method || "GET").toUpperCase(),
    unsafe = !["GET", "HEAD", "OPTIONS"].includes(method);
  if (unsafe && !csrf) await token();
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  if (unsafe) headers.set("X-CSRFToken", csrf);
  const r = await fetch("/api/v1" + path, {
    ...options,
    method,
    credentials: "include",
    cache: "no-store",
    headers,
  });
  if (r.status === 204) return undefined as T;
  const data = await r
    .json()
    .catch(() => ({ detail: "The server could not complete this request." }));
  if (!r.ok) {
    if (r.status === 403) csrf = "";
    throw new ApiError(describe(data), r.status, data);
  }
  if (
    [
      "/auth/login",
      "/auth/register",
      "/auth/otp/verify",
      "/auth/logout",
      "/auth/password/change",
    ].includes(path)
  )
    csrf = "";
  return data;
}
export function post<T = any>(
  path: string,
  data: unknown,
  headers: Record<string, string> = {},
) {
  return api<T>(path, { method: "POST", body: JSON.stringify(data), headers });
}
export function cash(value: string | number, currency: string, locale = "en") {
  const n = Number(value);
  if (!Number.isFinite(n) || !currency) return "—";
  try {
    return new Intl.NumberFormat(locale === "ar" ? "ar" : "en", {
      style: "currency",
      currency,
    }).format(n);
  } catch {
    return `${n.toFixed(2)} ${currency}`;
  }
}
export function field(item: any, key: string, locale: string) {
  return (
    (locale === "ar" && item?.[key + "_ar"]
      ? item[key + "_ar"]
      : item?.[key]) ?? ""
  );
}
export function safeImage(value: unknown) {
  if (typeof value !== "string") return "";
  if (value.startsWith("/") && !value.startsWith("//")) return value;
  try {
    const u = new URL(value);
    return u.protocol === "https:" ? value : "";
  } catch {
    return "";
  }
}
