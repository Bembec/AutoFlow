"use client";

import { Check } from "lucide-react";
import Link from "next/link";
import { useSyncExternalStore } from "react";

import { Card } from "@/components/ui";
import { type MessageKey, useI18n } from "@/lib/i18n";
import { useSession } from "@/lib/session";
import type { Onboarding, OnboardingStep } from "@/lib/types";
import { useApi } from "@/lib/useApi";

/** Where each step's button leads; `workflowId` is the shop's first workflow, if any. */
function stepLink(step: OnboardingStep, workflowId: number | undefined) {
  switch (step) {
    case "business":
      return "/settings#business";
    case "email":
      return "/connections";
    case "template":
      return "/get-started";
    case "test":
      return workflowId ? `/workflows/${workflowId}?tab=run` : "/get-started";
    case "publish":
      return workflowId ? `/workflows/${workflowId}` : "/get-started";
    case "live":
      return workflowId ? `/workflows/${workflowId}?tab=trigger` : "/get-started";
  }
}

// Hiding the checklist is a per-browser convenience, remembered per workspace
const hiddenKey = (workspaceId: number) => `luphina.onboarding.hidden.${workspaceId}`;
const listeners = new Set<() => void>();

function readHidden(workspaceId: number) {
  try {
    return window.localStorage.getItem(hiddenKey(workspaceId)) === "1";
  } catch {
    return false;
  }
}

function hide(workspaceId: number) {
  try {
    window.localStorage.setItem(hiddenKey(workspaceId), "1");
  } catch {
    // storage unavailable: the checklist stays visible
  }
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function OnboardingChecklist({ workflowId }: { workflowId?: number }) {
  const { base, workspace, can } = useSession();
  const { t } = useI18n();
  const { data } = useApi<Onboarding>(`${base}/onboarding`);
  const hidden = useSyncExternalStore(subscribe, () => readHidden(workspace.id), () => true);

  if (!data || data.complete || hidden || !can("member")) return null;

  const share = Math.round((data.completed / data.total) * 100);
  const next = data.steps.find((step) => !step.done)?.id;

  return (
    <Card className="mb-6 border-brand-200">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">{t("onb.title")}</h2>
          <p className="mt-1 max-w-2xl text-sm text-slate-500">{t("onb.subtitle")}</p>
        </div>
        <button onClick={() => hide(workspace.id)} className="text-sm text-slate-500 hover:text-slate-900">
          {t("onb.hide")}
        </button>
      </div>

      <div className="mt-4 flex items-center gap-3">
        <div
          className="h-2 flex-1 rounded-full bg-slate-100"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={data.total}
          aria-valuenow={data.completed}
          aria-label={t("onb.progress", { done: data.completed, total: data.total })}
        >
          <div className="h-2 rounded-full bg-brand-500 transition-all" style={{ width: `${share}%` }} />
        </div>
        <span className="text-sm tabular-nums text-slate-600">
          {t("onb.progress", { done: data.completed, total: data.total })}
        </span>
      </div>

      <ol className="mt-4 divide-y divide-slate-100">
        {data.steps.map((step, index) => {
          const isNext = step.id === next;
          return (
            <li key={step.id} className="flex items-center gap-3 py-3">
              <span
                className={`flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                  step.done
                    ? "bg-emerald-100 text-emerald-700"
                    : isNext
                      ? "bg-brand-600 text-white"
                      : "bg-slate-100 text-slate-500"
                }`}
              >
                {step.done ? <Check aria-label={t("onb.doneLabel")} className="size-4" /> : index + 1}
              </span>
              <div className="min-w-0 flex-1">
                <p className={`text-sm font-medium ${step.done ? "text-slate-400 line-through" : "text-slate-900"}`}>
                  {t(`onb.${step.id}` as MessageKey)}
                </p>
                {!step.done && <p className="text-xs text-slate-500">{t(`onb.${step.id}.hint` as MessageKey)}</p>}
              </div>
              {!step.done && (
                <Link
                  href={stepLink(step.id, workflowId)}
                  className={`shrink-0 rounded-lg px-3 py-1.5 text-sm font-medium ${
                    isNext
                      ? "bg-brand-600 text-white hover:bg-brand-500"
                      : "border border-slate-300 text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  {t(`onb.${step.id}.cta` as MessageKey)}
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </Card>
  );
}
