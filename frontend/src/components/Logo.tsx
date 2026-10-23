// Server-safe: used on public pages and inside the app.

import { BRAND } from "@/lib/brand";

/** Product mark + wordmark; both come from the brand settings. */
export function Logo({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 font-semibold ${className}`}>
      {/* eslint-disable-next-line @next/next/no-img-element -- static SVG, no optimisation needed */}
      <img src="/icon.svg" alt="" width={24} height={24} className="size-6 rounded-md" />
      <span>
        {BRAND.lead}
        <span className="text-brand-600">{BRAND.accent}</span>
      </span>
    </span>
  );
}
