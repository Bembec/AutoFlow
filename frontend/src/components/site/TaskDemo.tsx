"use client";

import {
  ArrowRight,
  Bot,
  Clock,
  FileText,
  type LucideIcon,
  Mail,
  ShieldCheck,
  Sheet,
  Sparkles,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { savePendingTask } from "@/lib/pendingTask";
import { useSiteText } from "@/lib/site-i18n";

interface PreviewStep {
  icon: LucideIcon;
  text: string;
  approval?: boolean;
}

/*
 * Website preview only: picks a hand-written example that matches the words
 * typed. After sign-up the real AI builder drafts the actual workflow.
 */
const PREVIEWS: { match: RegExp; steps: PreviewStep[] }[] = [
  {
    match: /cart|abandon|checkout|remind/i,
    steps: [
      { icon: Zap, text: "A customer starts a checkout" },
      { icon: Clock, text: "Wait 1 hour" },
      { icon: Bot, text: "Check whether they already bought" },
      { icon: Mail, text: "Email a friendly reminder with their cart link", approval: true },
    ],
  },
  {
    match: /review|rating|stars|feedback/i,
    steps: [
      { icon: Zap, text: "A new product review arrives" },
      { icon: Sparkles, text: "AI reads the review and its tone" },
      { icon: Bot, text: "AI drafts a polite, personal reply" },
      { icon: Mail, text: "Send the reply to the reviewer", approval: true },
    ],
  },
  {
    match: /supplier|receipt|bill|pdf|expense|spreadsheet|sheet/i,
    steps: [
      { icon: Zap, text: "A supplier invoice lands in your inbox" },
      { icon: Sparkles, text: "AI reads the PDF: supplier, date, total, tax" },
      { icon: Sheet, text: "Add a row to your bookkeeping spreadsheet" },
    ],
  },
  {
    match: /invoice|order|paid|sale|purchase/i,
    steps: [
      { icon: Zap, text: "An order is paid in your store" },
      { icon: FileText, text: "Create a numbered PDF invoice" },
      { icon: Bot, text: "Record the order and customer" },
      { icon: Mail, text: "Email the invoice to the customer", approval: true },
    ],
  },
];

const FALLBACK: PreviewStep[] = [
  { icon: Zap, text: "Something happens in one of your apps" },
  { icon: Sparkles, text: "AI works out what it means" },
  { icon: Bot, text: "Do what you described" },
  { icon: Mail, text: "Let you check anything that goes to a customer", approval: true },
];

const EXAMPLES = [
  "When an order is paid, email the customer a PDF invoice",
  "Remind people who leave items in their cart",
  "Draft replies to new product reviews for me to approve",
  "Put supplier invoices from my inbox into a spreadsheet",
];

function preview(task: string) {
  return PREVIEWS.find((item) => item.match.test(task))?.steps ?? FALLBACK;
}

export function TaskDemo() {
  const text = useSiteText();
  const [task, setTask] = useState(EXAMPLES[0]);
  // The matching runs on English keywords: example chips keep their English
  // meaning even when shown translated
  const [shown, setShown] = useState(EXAMPLES[0]);
  const steps = preview(shown);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-xl shadow-brand-900/5 sm:p-6">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          setShown(task);
        }}
      >
        <label htmlFor="demo-task" className="text-sm font-medium text-slate-700">
          {text("What should happen?")}
        </label>
        <div className="mt-2 flex flex-col gap-2 sm:flex-row">
          <input
            id="demo-task"
            value={task === EXAMPLES[0] ? text(task) : task}
            onChange={(event) => setTask(event.target.value)}
            maxLength={300}
            className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          />
          <button type="submit" className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-500">
            <Sparkles aria-hidden className="size-4" />
            {text("Show me")}
          </button>
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {EXAMPLES.map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => {
                setTask(text(example));
                setShown(example);
              }}
              className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-200"
            >
              {text(example)}
            </button>
          ))}
        </div>
      </form>

      <ol aria-live="polite" className="mt-5 space-y-2">
        {steps.map((step, index) => {
          const Icon = step.icon;
          return (
            <li key={`${shown}-${index}`} className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5">
              <span className={`flex size-8 shrink-0 items-center justify-center rounded-lg ${index === 0 ? "bg-brand-600 text-white" : "bg-white text-brand-600 ring-1 ring-slate-200"}`}>
                <Icon aria-hidden className="size-4" />
              </span>
              <span className="flex-1 text-sm text-slate-800">{text(step.text)}</span>
              {step.approval && (
                <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-800 ring-1 ring-amber-600/20">
                  <ShieldCheck aria-hidden className="size-3" />
                  {text("You approve")}
                </span>
              )}
            </li>
          );
        })}
      </ol>

      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
        <p className="text-xs text-slate-500">{text("A preview. After sign-up, the AI drafts the real workflow from your words.")}</p>
        <Link
          href="/register"
          onClick={() => savePendingTask(task)}
          className="inline-flex items-center gap-1.5 text-sm font-medium text-brand-700 hover:text-brand-900"
        >
          {text("Build this for real")}
          <ArrowRight aria-hidden className="size-4" />
        </Link>
      </div>
    </div>
  );
}
