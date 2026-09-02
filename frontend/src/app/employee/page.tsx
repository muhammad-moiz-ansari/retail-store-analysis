"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/** Legacy employee route retained so existing bookmarks use the canonical workspace. */
export default function EmployeeRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/employee-home");
  }, [router]);

  return <div className="min-h-screen bg-bg" aria-label="Redirecting to employee workspace" />;
}
