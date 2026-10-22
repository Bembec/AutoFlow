import { Suspense } from "react";

import { AppShell } from "@/components/AppShell";

// Everything inside the app is per-user and rendered in the browser.
// The Suspense boundary lets URL hooks (params, pathname) resolve at
// request time, as required when cacheComponents is enabled.
// Signed-in pages load each user's data in the browser, so they show a
// loading state rather than an instant prefetched shell.
export const instant = false;

export default function AppLayout({ children }: LayoutProps<"/">) {
  return (
    <Suspense fallback={<div className="p-8 text-sm text-slate-500">Loading…</div>}>
      <AppShell>{children}</AppShell>
    </Suspense>
  );
}
