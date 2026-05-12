import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8080";

// Headers we forward from the browser to the backend.  Auth rides on
// `authorization`; everything else is either spoofable client trash
// (x-forwarded-*, cookie) or hop-by-hop and unsafe to forward.
const REQUEST_HEADER_ALLOWLIST = new Set([
  "accept",
  "accept-encoding",
  "accept-language",
  "authorization",
  "content-type",
  "content-length",
  "user-agent",
]);

// Headers we surface from the backend to the browser.  Anything else
// (server, x-powered-by, internal x-*) stays internal.
const RESPONSE_HEADER_ALLOWLIST = new Set([
  "cache-control",
  "content-disposition",
  "content-language",
  "content-length",
  "content-type",
  "etag",
  "last-modified",
  "location",
  "vary",
]);

function filteredRequestHeaders(req: NextRequest): Headers {
  const out = new Headers();
  req.headers.forEach((value, key) => {
    if (REQUEST_HEADER_ALLOWLIST.has(key.toLowerCase())) {
      out.set(key, value);
    }
  });
  return out;
}

function filteredResponseHeaders(src: Headers): Headers {
  const out = new Headers();
  src.forEach((value, key) => {
    if (RESPONSE_HEADER_ALLOWLIST.has(key.toLowerCase())) {
      out.set(key, value);
    }
  });
  return out;
}

async function proxy(req: NextRequest): Promise<NextResponse> {
  const path = req.nextUrl.pathname.replace(/^\/api/, "");
  const url = `${BACKEND}${path}${req.nextUrl.search}`;
  const res = await fetch(url, {
    method: req.method,
    headers: filteredRequestHeaders(req),
    body:
      req.method !== "GET" && req.method !== "HEAD" ? req.body : undefined,
    // @ts-expect-error — duplex required for streaming body in Node fetch
    duplex: "half",
  });
  return new NextResponse(res.body, {
    status: res.status,
    headers: filteredResponseHeaders(res.headers),
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
