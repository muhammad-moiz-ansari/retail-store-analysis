import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { POS_SESSION_COOKIE } from "@/lib/pos-auth";

export async function POST() {
  const cookieStore = await cookies();
  cookieStore.delete(POS_SESSION_COOKIE);
  return NextResponse.json({ ok: true });
}

