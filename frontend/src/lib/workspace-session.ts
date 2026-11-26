import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { resolveAuthConfig } from "./auth-config";
import { SESSION_COOKIE, verifySession } from "./session-auth";

export async function requireWorkspaceSession(role?: "Manager" | "Employee") {
  if (!resolveAuthConfig()) redirect("/login");
  const cookieStore = await cookies();
  const session = verifySession(cookieStore.get(SESSION_COOKIE)?.value);
  if (!session) redirect("/login");
  if (role && session.role !== role) {
    redirect(session.role === "Manager" ? "/manager/home" : "/employee/home");
  }
}
