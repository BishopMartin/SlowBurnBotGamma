import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8080";

async function proxy(req: NextRequest): Promise<NextResponse> {
  const path = req.nextUrl.pathname.replace(/^\/api/, "");
  const url = `${BACKEND}${path}${req.nextUrl.search}`;
  const headers = new Headers(req.headers);
  headers.delete("host");
  const res = await fetch(url, {
    method: req.method,
    headers,
    body:
      req.method !== "GET" && req.method !== "HEAD" ? req.body : undefined,
    // @ts-expect-error — duplex required for streaming body in Node fetch
    duplex: "half",
  });
  return new NextResponse(res.body, { status: res.status, headers: res.headers });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
