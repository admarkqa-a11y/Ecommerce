/** Runtime upstream: no client credentials or client identity in the built image. */
export async function proxy(
  request: Request,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  if (
    path.some(
      (s) => s === ".." || s === "." || s.includes("/") || s.includes("\\"),
    )
  )
    return new Response("Invalid path", { status: 400 });
  const base = process.env.API_ORIGIN || "http://127.0.0.1:8000";
  const target = new URL(
    "/api/" + path.map(encodeURIComponent).join("/"),
    base,
  );
  target.search = new URL(request.url).search;
  const length = Number(request.headers.get("content-length") || 0);
  if (length > 11 * 1024 * 1024)
    return Response.json({ detail: "Upload exceeds 11 MiB." }, { status: 413 });
  const headers = new Headers();
  if (process.env.API_HTTPS_TERMINATED === "true")
    headers.set("X-Forwarded-Proto", "https");
  for (const key of [
    "accept",
    "content-type",
    "cookie",
    "origin",
    "referer",
    "x-csrftoken",
    "idempotency-key",
    "user-agent",
  ]) {
    const value = request.headers.get(key);
    if (value) headers.set(key, value);
  }
  try {
    const response = await fetch(target, {
      method: request.method,
      headers,
      body: ["GET", "HEAD"].includes(request.method)
        ? undefined
        : await request.arrayBuffer(),
      redirect: "manual",
      cache: "no-store",
      signal: AbortSignal.timeout(65000),
    });
    const outgoing = new Headers({ "Cache-Control": "no-store" });
    for (const key of [
      "content-type",
      "content-disposition",
      "retry-after",
      "allow",
    ]) {
      const value = response.headers.get(key);
      if (value) outgoing.set(key, value);
    }
    for (const cookie of response.headers.getSetCookie())
      outgoing.append("set-cookie", cookie);
    // Never follow an upstream redirect while forwarding session cookies.
    if (response.status >= 300 && response.status < 400)
      return Response.json(
        { detail: "Unexpected API redirect." },
        { status: 502 },
      );
    return new Response(response.body, {
      status: response.status,
      headers: outgoing,
    });
  } catch {
    return Response.json(
      { detail: "The service is temporarily unavailable. Please retry." },
      { status: 503 },
    );
  }
}
