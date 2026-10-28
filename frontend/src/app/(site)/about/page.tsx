import { History, type LucideIcon, RefreshCw, ShieldCheck } from "lucide-react";
import { S } from "@/lib/site-i18n";
import type { Metadata } from "next";

import { SiteCta, SiteHero } from "@/components/site/SiteChrome";
import { BRAND } from "@/lib/brand";

export const instant = true;

export const metadata: Metadata = { title: "About" };

// Product first; the founder story is the quieter section below it (brand brief).
const VALUES: { icon: LucideIcon; title: string; text: string }[] = [
  { icon: RefreshCw, title: "Dependable", text: "Automatic retries, time limits, and protection against doing the same thing twice." },
  { icon: History, title: "Understandable", text: "Every run explained step by step, in plain language." },
  {
    icon: ShieldCheck,
    title: "In your control",
    text: "Anything that reaches your customers waits for a person's approval, and one emergency stop pauses everything.",
  },
];

export default function About() {
  return (
    <>
      <SiteHero eyebrow="About Luphina" title="Built to make progress easier.">
        <p>
          <S t={"Luphina helps businesses simplify repetitive work, connect their tools, and turn everyday processes into intelligent workflows."} />
        </p>
        <p className="mt-3 text-base">
          <S t={"Reduce manual effort, bring customer interactions together, and give people more control over how work gets done."} />
        </p>
      </SiteHero>

      <section className="mx-auto max-w-6xl px-4 pb-16 sm:px-6">
        <h2 className="text-center text-2xl font-semibold tracking-tight"><S t={"How we build"} /></h2>
        <div className="mt-8 grid gap-6 sm:grid-cols-3">
          {VALUES.map(({ icon: Icon, title, text }) => (
            <div key={title} className="rounded-2xl border border-slate-200 bg-white p-6">
              <Icon aria-hidden className="size-6 text-brand-600" />
              <h3 className="mt-4 font-semibold"><S t={title} /></h3>
              <p className="mt-2 text-sm text-slate-600"><S t={text} /></p>
            </div>
          ))}
        </div>
      </section>

      <section id="our-story" className="scroll-mt-20 bg-lilac/60">
        <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
          <h2 className="font-display text-2xl font-semibold tracking-tight text-ink"><S t={"Our story"} /></h2>
          <p className="mt-4 text-lg leading-relaxed text-slate-700">
            <S t={"The name Luphina honours the founder's mother, whose strength, resourcefulness, and commitment to helping others inspired a simple belief: difficult circumstances should not end the search for a better way. That belief informs how we build: practical tools that help people make progress."} />
          </p>
          <p className="mt-6 font-display text-slate-600 italic"><S t={BRAND.philosophy} /></p>
        </div>
      </section>

      <section id="contact" className="mx-auto max-w-3xl scroll-mt-20 px-4 py-12 text-center sm:px-6">
        <h2 className="text-xl font-semibold"><S t={"Contact"} /></h2>
        <p className="mt-2 text-slate-600">
          <S t={"Questions or feedback? Email us at {email}."} vars={{ email: BRAND.supportEmail }} />
        </p>
        <a href={`mailto:${BRAND.supportEmail}`} className="mt-3 inline-block font-medium text-brand-700 underline">
          {BRAND.supportEmail}
        </a>
      </section>

      <SiteCta />
    </>
  );
}
