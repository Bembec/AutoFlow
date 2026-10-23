import Link from "next/link";

import { Logo } from "@/components/Logo";

// Public, static page: should always render instantly
export const instant = true;

const STEPS = [
  {
    title: "Describe it",
    text: "“When a customer emails about pricing, quote them in USD and reply after I approve.”",
  },
  {
    title: "Review the workflow",
    text: "AutoFlow drafts each step on a canvas, asks about missing details, and lets you test with sample data.",
  },
  {
    title: "Switch it on",
    text: "It runs reliably — retries, approvals for anything sensitive, and a log of every step.",
  },
];

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col px-4 py-8 sm:px-6">
      <header className="flex items-center justify-between">
        <Logo className="text-lg" />
        <nav className="flex gap-2 text-sm">
          <Link href="/login" className="rounded-lg px-3 py-2 text-slate-700 hover:bg-white">
            Sign in
          </Link>
          <Link href="/register" className="rounded-lg bg-brand-600 px-3 py-2 font-medium text-white hover:bg-brand-500">
            Start free
          </Link>
        </nav>
      </header>

      <section className="py-20 text-center sm:py-28">
        <p className="text-sm font-medium text-brand-600">Save 10+ hours a week. No code. Live in minutes.</p>
        <h1 className="mx-auto mt-4 max-w-3xl text-4xl font-semibold tracking-tight sm:text-5xl">
          Tell it what you want done.
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-lg text-slate-600">
          AutoFlow builds the workflow, connects your apps, and runs it for you — with a human in the loop for anything that matters.
        </p>
        <div className="mt-8 flex justify-center gap-3">
          <Link href="/register" className="rounded-lg bg-brand-600 px-5 py-3 font-medium text-white hover:bg-brand-500">
            Build your first workflow
          </Link>
        </div>
      </section>

      <section className="grid gap-4 pb-16 sm:grid-cols-3">
        {STEPS.map((step, index) => (
          <div key={step.title} className="rounded-xl border border-slate-200 bg-white p-5">
            <p className="text-sm font-semibold text-brand-600">{index + 1}</p>
            <h2 className="mt-1 font-semibold">{step.title}</h2>
            <p className="mt-2 text-sm text-slate-600">{step.text}</p>
          </div>
        ))}
      </section>
    </main>
  );
}
