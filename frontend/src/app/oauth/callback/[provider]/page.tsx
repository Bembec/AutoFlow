import { Suspense } from "react";

import { OAuthCallback } from "./OAuthCallback";

// The provider (e.g. Google) sends the browser here after sign-in.
export default function OAuthCallbackPage() {
  return (
    <Suspense fallback={<p className="p-8 text-sm text-slate-500">Finishing sign-in…</p>}>
      <OAuthCallback />
    </Suspense>
  );
}
