"use client";

// Website sections that read the live product catalogue (plans and
// templates), so the site never disagrees with the app.

import { Check } from "lucide-react";
import Link from "next/link";

import { ErrorNote, Skeleton } from "@/components/ui";
import type { TemplateInfo } from "@/lib/types";
import { useI18n } from "@/lib/i18n";
import { useSiteText } from "@/lib/site-i18n";
import { useApi } from "@/lib/useApi";

interface Plan {
  name: string;
  label: string;
  price_usd_month: number | null;
  included_tasks: number | null;
  max_workflows: number | null;
  max_seats: number | null;
  description: string;
}


function CardSkeletons({ cards }: { cards: number }) {
  return (
    <>
      {Array.from({ length: cards }, (_, index) => (
        <div key={index} className="space-y-3 rounded-2xl border border-slate-200 p-6">
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-8 w-1/2" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-2/3" />
        </div>
      ))}
    </>
  );
}

export function PlansGrid() {
  const { data: plans, error } = useApi<Plan[]>("/plans");
  const text = useSiteText();
  const { language } = useI18n();
  const number = (value: number) => value.toLocaleString(language);

  return (
    <>
      <ErrorNote message={error} />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {!plans && !error && <CardSkeletons cards={5} />}
        {plans?.map((plan) => {
          const custom = plan.price_usd_month === null;
          const featured = plan.name === "starter";
          return (
            <div
              key={plan.name}
              className={`flex flex-col rounded-2xl border p-6 ${featured ? "border-brand-500 ring-1 ring-brand-500" : "border-slate-200"}`}
            >
              {featured && <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-brand-700">{text("Good place to start")}</p>}
              <h2 className="font-semibold">{plan.label}</h2>
              <p className="mt-1 text-sm text-slate-500">{text(plan.description)}</p>
              <p className="mt-4 text-3xl font-semibold">
                {custom ? text("Custom") : `$${plan.price_usd_month}`}
                {!custom && <span className="text-sm font-normal text-slate-500"> {text("/ month")}</span>}
              </p>
              <ul className="mt-5 flex-1 space-y-2 text-sm text-slate-700">
                {[
                  plan.included_tasks === null
                    ? text("Unlimited tasks a month")
                    : text("{n} tasks a month", { n: number(plan.included_tasks) }),
                  plan.max_workflows === null
                    ? text("Unlimited workflows")
                    : text("{n} workflows", { n: number(plan.max_workflows) }),
                  plan.max_seats === null
                    ? text("Unlimited team seats")
                    : plan.max_seats === 1 ? text("1 team seat") : text("{n} team seats", { n: number(plan.max_seats) }),
                ].map((line) => (
                  <li key={line} className="flex gap-2">
                    <Check aria-hidden className="mt-0.5 size-4 shrink-0 text-emerald-600" />
                    {line}
                  </li>
                ))}
              </ul>
              <Link
                href="/register"
                className={`mt-6 rounded-lg px-4 py-2 text-center text-sm font-medium ${
                  featured ? "bg-brand-600 text-white hover:bg-brand-500" : "border border-slate-300 text-slate-800 hover:bg-slate-50"
                }`}
              >
                {custom ? text("Talk to us") : plan.price_usd_month === 0 ? text("Start free") : text("Choose {plan}", { plan: plan.label })}
              </Link>
            </div>
          );
        })}
      </div>
    </>
  );
}

export function TemplateGallery() {
  const { data: templates, error } = useApi<TemplateInfo[]>("/templates");
  const text = useSiteText();
  const categories = [...new Set(templates?.map((template) => template.category))];

  return (
    <>
      <ErrorNote message={error} />
      {!templates && !error && (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <CardSkeletons cards={6} />
        </div>
      )}
      {categories.map((category) => (
        <section key={category} className="mb-12">
          <h2 className="mb-4 text-xl font-semibold">{category}</h2>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {templates
              ?.filter((template) => template.category === category)
              .map((template) => (
                <article key={template.slug} className="flex flex-col rounded-2xl border border-slate-200 p-6">
                  <h3 className="font-semibold">{template.name}</h3>
                  <p className="mt-2 flex-1 text-sm text-slate-600">{template.description}</p>
                  {template.requires.length > 0 && (
                    <details className="mt-4 text-sm">
                      <summary className="cursor-pointer text-slate-500 hover:text-slate-800">{text("What it needs")}</summary>
                      <ul className="mt-2 list-disc space-y-1 pl-5 text-slate-600">
                        {template.requires.map((item) => <li key={item}>{item}</li>)}
                      </ul>
                    </details>
                  )}
                  <Link href="/register" className="mt-5 text-sm font-medium text-brand-700 hover:text-brand-900">
                    {text("Use this template →")}
                  </Link>
                </article>
              ))}
          </div>
        </section>
      ))}
    </>
  );
}
