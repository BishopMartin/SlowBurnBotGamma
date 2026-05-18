import { NextResponse } from "next/server";
import { loadTheme } from "@/lib/theme-loader";

export async function GET(
  _req: Request,
  context: { params: Promise<{ slug: string }> },
) {
  const { slug } = await context.params;
  try {
    const theme = loadTheme(slug);
    return NextResponse.json({ name: theme.name, css: theme.css });
  } catch {
    return NextResponse.json({ error: "not found" }, { status: 404 });
  }
}
