import { NextRequest, NextResponse } from "next/server";
export function proxy(request: NextRequest) {
  const headers = new Headers(request.headers);
  headers.set(
    "x-retail-locale",
    request.nextUrl.pathname.split("/")[1] === "ar" ? "ar" : "en",
  );
  return NextResponse.next({ request: { headers } });
}
export const config = { matcher: ["/((?!api|_next|favicon.ico).*)"] };
