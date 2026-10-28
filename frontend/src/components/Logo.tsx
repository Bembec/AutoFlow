// Server-safe: used on public pages and inside the app.

import { BRAND } from "@/lib/brand";

/** The approved Luphina mark + wordmark; both come from the brand settings. */
export function Logo({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 font-semibold ${className}`}>
      {/* eslint-disable-next-line @next/next/no-img-element -- small static mark, no optimisation needed */}
      <img src={BRAND.mark} alt="" width={20} height={24} className="h-7 w-auto rounded-md" />
      <span className="font-display text-lg tracking-tight text-ink">{BRAND.name}</span>
    </span>
  );
}
