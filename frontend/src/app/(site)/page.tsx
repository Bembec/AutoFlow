import {
  Bot,
  History,
  type LucideIcon,
  RefreshCw,
  ShieldCheck,
  Smartphone,
  Users,
} from "lucide-react";
import { S } from "@/lib/site-i18n";
import Link from "next/link";

import { SiteCta, ctaClass, secondaryCtaClass } from "@/components/site/SiteChrome";
import { TaskDemo } from "@/components/site/TaskDemo";

// Public, static page: should always render instantly
export const instant = true;

const WORKS_WITH = ["Shopify", "WooCommerce", "Gmail and any email", "Google Sheets", "Airtable", "Slack", "Any REST API"];

const STEPS = [
  {
    title: "Describe it",
    text: "Type what should happen, in your own words. AutoFlow asks about anything unclear.",
  },
  {
    title: "Test it safely",
    text: "See every step on a diagram and run it with an example order. Nothing reaches customers.",
  },
  {
    title: "Switch it on",
    text: "Publish, and it runs on real orders, with your approval for anything that matters.",
  },
];

const FEATURES: { icon: LucideIcon; title: string; text: string }[] = [
  {
    icon: Bot,
    title: "Built from plain words",
    text: "The AI builder turns a sentence into a working workflow you can read, edit and test.",
  },
  {
    icon: ShieldCheck,
    title: "You approve what matters",
    text: "Emails to customers wait for a tap of approval. One emergency stop pauses everything.",
  },
  {
    icon: RefreshCw,
    title: "Dependable by design",
    text: "Automatic retries, time limits, and protection against doing the same thing twice.",
  },
  {
    icon: History,
    title: "See exactly what happened",
    text: "Every run explained step by step, in plain language. Retry a failed step in one click.",
  },
  {
    icon: Smartphone,
    title: "Approve from your phone",
    text: "Add it to your home screen and clear approvals in seconds, wherever you are.",
  },
  {
    icon: Users,
    title: "Made for teams",
    text: "Invite your team with roles, keep an activity log, and secure sign-in with two-factor login.",
  },
];

const TEMPLATES = [
  { name: "Order → invoice", text: "A numbered PDF invoice for every paid order, emailed after your OK." },
  { name: "Abandoned-cart follow-up", text: "A friendly reminder an hour later, skipped if they already bought." },
  { name: "Review reply assistant", text: "AI drafts a personal reply to each review; you approve before it goes." },
];

export default function Home() {
  return (
    <>
      <section className="relative overflow-hidden">
        <div aria-hidden className="absolute inset-x-0 top-0 -z-10 h-[520px] bg-gradient-to-b from-brand-50 to-white" />
        <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 pt-16 pb-20 sm:px-6 lg:grid-cols-2 lg:pt-24">
          <div>
            <p className="inline-flex rounded-full bg-white px-3 py-1 text-sm font-medium text-brand-700 ring-1 ring-brand-200">
              <S t={"Automation for online shops"} />
            </p>
            <h1 className="mt-5 text-4xl font-semibold tracking-tight text-slate-900 sm:text-6xl">
              <S t={"Tell it what you want done."} />
            </h1>
            <p className="mt-5 max-w-xl text-lg text-slate-600">
              <S t={"AutoFlow builds the workflow, connects your store and apps, and runs it for you. A person stays in the loop for anything that matters."} />
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/register" className={ctaClass}><S t={"Start free"} /></Link>
              <Link href="/templates" className={secondaryCtaClass}><S t={"See templates"} /></Link>
            </div>
            <p className="mt-4 text-sm text-slate-500"><S t={"Free plan available. No card needed to try it."} /></p>
          </div>
          <TaskDemo />
        </div>
      </section>

      <section aria-label="Works with" className="border-y border-slate-100 bg-slate-50">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-center gap-x-8 gap-y-3 px-4 py-6 text-sm font-medium text-slate-500 sm:px-6">
          <span className="text-slate-400">Works with</span>
          {WORKS_WITH.map((name) => <span key={name}><S t={name} /></span>)}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
        <h2 className="text-center text-3xl font-semibold tracking-tight"><S t={"Live in three steps"} /></h2>
        <ol className="mt-10 grid gap-6 sm:grid-cols-3">
          {STEPS.map((step, index) => (
            <li key={step.title} className="rounded-2xl border border-slate-200 p-6">
              <span className="flex size-9 items-center justify-center rounded-full bg-brand-600 font-semibold text-white">
                {index + 1}
              </span>
              <h3 className="mt-4 font-semibold"><S t={step.title} /></h3>
              <p className="mt-2 text-sm text-slate-600"><S t={step.text} /></p>
            </li>
          ))}
        </ol>
      </section>

      <section className="bg-slate-50">
        <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
          <h2 className="max-w-2xl text-3xl font-semibold tracking-tight"><S t={"Powerful underneath. Simple on top."} /></h2>
          <p className="mt-3 max-w-2xl text-slate-600">
            <S t={"The reliability of an engineering tool, explained in words a shop owner uses."} />
          </p>
          <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map(({ icon: Icon, title, text }) => (
              <div key={title} className="rounded-2xl bg-white p-6 ring-1 ring-slate-200">
                <span className="flex size-10 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                  <Icon aria-hidden className="size-5" />
                </span>
                <h3 className="mt-4 font-semibold"><S t={title} /></h3>
                <p className="mt-2 text-sm text-slate-600"><S t={text} /></p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-3xl font-semibold tracking-tight"><S t={"Start from a ready-made automation"} /></h2>
            <p className="mt-3 max-w-2xl text-slate-600"><S t={"Built for the jobs online shops repeat every day."} /></p>
          </div>
          <Link href="/templates" className="text-sm font-medium text-brand-700 hover:text-brand-900"><S t={"All templates →"} /></Link>
        </div>
        <div className="mt-8 grid gap-6 md:grid-cols-3">
          {TEMPLATES.map((template) => (
            <div key={template.name} className="rounded-2xl border border-slate-200 p-6">
              <h3 className="font-semibold"><S t={template.name} /></h3>
              <p className="mt-2 text-sm text-slate-600"><S t={template.text} /></p>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 pb-20 sm:px-6">
        <div className="grid gap-6 rounded-2xl border border-slate-200 p-8 md:grid-cols-[1fr_auto] md:items-center">
          <div className="flex gap-4">
            <span className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600">
              <ShieldCheck aria-hidden className="size-6" />
            </span>
            <div>
              <h2 className="text-xl font-semibold"><S t={"Your store, your customers, your data"} /></h2>
              <p className="mt-2 max-w-2xl text-sm text-slate-600">
                <S t={"Encrypted credentials, separate workspaces, signed webhooks, approvals, an activity log, and export or delete your data at any time."} />
              </p>
            </div>
          </div>
          <Link href="/security" className={secondaryCtaClass}><S t={"How we keep it safe"} /></Link>
        </div>
      </section>

      <SiteCta />
    </>
  );
}
