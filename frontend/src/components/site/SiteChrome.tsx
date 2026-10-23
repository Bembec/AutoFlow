// Header and footer of the public website. Server components: no JavaScript
// needed (the mobile menu is a <details> element).

import { SiteAccountLinks, StartOrOpen } from "@/components/site/SiteAccountLinks";
import { SiteLanguagePicker } from "@/components/site/SiteLanguagePicker";
import { S } from "@/lib/site-i18n";
import { Menu } from "lucide-react";
import Link from "next/link";

import { Logo } from "@/components/Logo";
import { BRAND } from "@/lib/brand";

const LINKS = [
  { href: "/templates", label: "Templates" },
  { href: "/integrations", label: "Integrations" },
  { href: "/pricing", label: "Pricing" },
  { href: "/security", label: "Security" },
];

export const ctaClass =
  "inline-flex items-center justify-center gap-2 rounded-lg bg-brand-600 px-5 py-3 font-medium text-white shadow-sm transition-colors hover:bg-brand-500";
export const secondaryCtaClass =
  "inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-5 py-3 font-medium text-slate-800 transition-colors hover:bg-slate-50";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/70 bg-white/85 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <Link href="/" aria-label={`${BRAND.name} home`}>
          <Logo className="text-lg" />
        </Link>
        <nav aria-label="Main" className="hidden items-center gap-1 text-sm md:flex">
          {LINKS.map((link) => (
            <Link key={link.href} href={link.href} className="rounded-lg px-3 py-2 text-slate-600 hover:bg-slate-100 hover:text-slate-900">
              <S t={link.label} />
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-2 text-sm">
          <SiteLanguagePicker />
          <SiteAccountLinks />
          <details className="relative md:hidden">
            <summary className="flex cursor-pointer list-none items-center rounded-lg border border-slate-300 p-2 [&::-webkit-details-marker]:hidden">
              <Menu aria-hidden className="size-4" />
              <span className="sr-only"><S t={"Menu"} /></span>
            </summary>
            <nav aria-label="Main" className="absolute right-0 mt-2 w-48 rounded-xl border border-slate-200 bg-white p-2 shadow-lg">
              {LINKS.map((link) => (
                <Link key={link.href} href={link.href} className="block rounded-lg px-3 py-2 text-slate-700 hover:bg-slate-100">
                  <S t={link.label} />
                </Link>
              ))}
              <SiteAccountLinks variant="menu" />
            </nav>
          </details>
        </div>
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 text-sm sm:grid-cols-[2fr_1fr_1fr] sm:px-6">
        <div>
          <Logo />
          <p className="mt-3 max-w-xs text-slate-500"><S t={BRAND.tagline} /></p>
        </div>
        <div>
          <p className="font-medium text-slate-900"><S t={"Product"} /></p>
          <ul className="mt-3 space-y-2 text-slate-600">
            {LINKS.map((link) => (
              <li key={link.href}>
                <Link href={link.href} className="hover:text-slate-900"><S t={link.label} /></Link>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="font-medium text-slate-900"><S t={"Account"} /></p>
          <ul className="mt-3 space-y-2 text-slate-600">
            <li><Link href="/register" className="hover:text-slate-900"><S t={"Create an account"} /></Link></li>
            <li><Link href="/login" className="hover:text-slate-900"><S t="Sign in" /></Link></li>
            <li><Link href="/report-abuse" className="hover:text-slate-900"><S t="Report abuse" /></Link></li>
          </ul>
        </div>
      </div>
      <p className="border-t border-slate-100 py-4 text-center text-xs text-slate-400">© {BRAND.name}</p>
    </footer>
  );
}

/** Page title block shared by the inner site pages. */
export function SiteHero({ eyebrow, title, children }: { eyebrow: string; title: string; children?: React.ReactNode }) {
  return (
    <section className="mx-auto max-w-3xl px-4 pt-16 pb-10 text-center sm:px-6 sm:pt-20">
      <p className="text-sm font-semibold text-brand-600"><S t={eyebrow} /></p>
      <h1 className="mt-3 text-4xl font-semibold tracking-tight text-slate-900 sm:text-5xl"><S t={title} /></h1>
      {children && <div className="mt-5 text-lg text-slate-600">{children}</div>}
    </section>
  );
}

/** Closing call to action used at the bottom of site pages. */
export function SiteCta({ title = "Your first automation is five minutes away." }: { title?: string }) {
  return (
    <section className="mx-auto max-w-6xl px-4 pb-20 sm:px-6">
      <div className="rounded-2xl bg-brand-950 px-6 py-12 text-center text-white sm:px-12">
        <h2 className="text-2xl font-semibold sm:text-3xl"><S t={title} /></h2>
        <p className="mx-auto mt-3 max-w-xl text-brand-100">
          <S t={"Free to start. Test with sample data first: nothing reaches your customers until you switch it on."} />
        </p>
        <StartOrOpen className="mt-6 inline-flex rounded-lg bg-white px-5 py-3 font-medium text-brand-900 hover:bg-brand-50" />
      </div>
    </section>
  );
}
