import { Suspense } from "react";

import { OAuthCallback } from "./OAuthCallback";

// Finishing sign-in happens in the browser after the provider redirects here.
export const instant = false;

// The provider (e.g. Google) sends the browser here after sign-in.
export default function OAuthCallbackPage() {
  return (
    <Suspense fallback={<p className="p-8 text-sm text-slate-500">Finishing sign-in…</p>}>
      <OAuthCallback />
    </Suspense>
  );
}
