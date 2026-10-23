import type { Metadata } from "next";

import { SiteCta, SiteHero } from "@/components/site/SiteChrome";
import { PlansGrid } from "@/components/site/SiteLists";

export const instant = true;

export const metadata: Metadata = { title: "Pricing" };

const FAQ = [
  {
    q: "What counts as a task?",
    a: "A step that succeeds and does something in an app or with AI, for example sending an email or creating an invoice. Failed steps, retries and test runs are free.",
  },
  {
    q: "What happens if I run out of tasks?",
    a: "You choose: keep running and pay for what you use, or pause billable steps at the limit. You get an alert before you get there.",
  },
  {
    q: "Can I change or cancel my plan?",
    a: "Yes, at any time from Plan & usage. Changes take effect right after payment.",
  },
  {
    q: "Do I need a card to start?",
    a: "No. The free plan is enough to build, test and run your first automations.",
  },
];

export default function PricingPage() {
  return (
    <>
      <SiteHero eyebrow="Pricing" title="Pay for work that gets done">
        <p>Start free. Upgrade when your automations are saving you time. Prices in US dollars.</p>
      </SiteHero>
      <div className="mx-auto max-w-6xl px-4 pb-16 sm:px-6">
        <PlansGrid />
      </div>
      <section className="mx-auto max-w-3xl px-4 pb-20 sm:px-6">
        <h2 className="text-2xl font-semibold">Questions</h2>
        <dl className="mt-6 divide-y divide-slate-200">
          {FAQ.map((item) => (
            <div key={item.q} className="py-5">
              <dt className="font-medium text-slate-900">{item.q}</dt>
              <dd className="mt-2 text-sm text-slate-600">{item.a}</dd>
            </div>
          ))}
        </dl>
      </section>
      <SiteCta />
    </>
  );
}
