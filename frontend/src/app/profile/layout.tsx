import type { ReactNode } from "react";
import { requireWorkspaceSession } from "@/lib/workspace-session";

export default async function WorkspaceLayout({ children }: { children: ReactNode }) {
  await requireWorkspaceSession();
  return children;
}
