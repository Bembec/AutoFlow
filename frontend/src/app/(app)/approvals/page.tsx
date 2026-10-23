"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Button, Card, EmptyState, ErrorNote, JsonBlock, Loading, PageHeader, StatusBadge, formatTime, inputClass } from "@/components/ui";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";
import { type MessageKey, useI18n } from "@/lib/i18n";
import type { Approval } from "@/lib/types";
import { useAction, useApi } from "@/lib/useApi";

export default function ApprovalsPage() {
  const { base } = useSession();
  const [view, setView] = useState<"pending" | "history">("pending");
  const path = view === "pending" ? `${base}/approvals?status=pending` : `${base}/approvals`;
  const { data, error, loading, reload } = useApi<Approval[]>(path);
  const items = view === "history" ? data?.filter((a) => a.status !== "pending") : data;
  const { t } = useI18n();
  // Notification links open one approval: /approvals?focus=<id>
  const focus = Number(useSearchParams().get("focus")) || null;

  return (
    <>
      <PageHeader
        title={t("appr.title")}
        description={t("appr.subtitle")}
      />
      <div className="mb-4 flex gap-2">
        {(["pending", "history"] as const).map((item) => (
          <button
            key={item}
            onClick={() => setView(item)}
            className={`rounded-full px-3 py-1 text-sm ${view === item ? "bg-indigo-600 text-white" : "bg-white text-slate-600 ring-1 ring-slate-200"}`}
          >
            {item === "pending" ? t("appr.waiting") : t("appr.decided")}
          </button>
        ))}
      </div>
      <ErrorNote message={error} />
      {loading && !data ? (
        <Loading />
      ) : !items || items.length === 0 ? (
        <EmptyState title={view === "pending" ? t("appr.nothingWaiting") : t("appr.noDecisions")} />
      ) : (
        <div className="space-y-4">
          {items.map((approval) => (
            <ApprovalCard key={approval.id} approval={approval} onDecided={reload} focused={approval.id === focus} />
          ))}
        </div>
      )}
    </>
  );
}

function title(approval: Approval, t: (key: MessageKey, vars?: Record<string, string | number>) => string) {
  if (approval.kind === "classification") return t("appr.checkCategory");
  if (approval.kind === "email") return t("appr.sendEmail");
  const name = approval.payload.step_name ?? "";
  if (approval.payload.review) return t("appr.reviewResult", { name });
  return t("appr.approveStep", { name });
}

function ApprovalCard({
  approval,
  onDecided,
  focused = false,
}: {
  approval: Approval;
  onDecided: () => void;
  focused?: boolean;
}) {
  const { base, can } = useSession();
  const { t } = useI18n();
  const cardRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (focused) cardRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [focused]);
  const action = useAction();
  const [category, setCategory] = useState<string>(approval.payload.suggested_category ?? "");
  const [output, setOutput] = useState(JSON.stringify(approval.payload.output ?? {}, null, 2));
  const pending = approval.status === "pending";
  const isReview = approval.kind === "step" && approval.payload.review;
  const email: Record<string, unknown> | undefined =
    approval.kind === "email" ? approval.payload : approval.payload.inputs;
  const looksLikeEmail = Boolean(email && "subject" in email && "body" in email);

  async function decide(approve: boolean) {
    let body: Record<string, unknown> = {};

    if (approve && approval.kind === "classification" && category !== approval.payload.suggested_category) {
      body = { category };
    }
    if (approve && isReview) {
      try {
        const corrected = JSON.parse(output);
        if (JSON.stringify(corrected) !== JSON.stringify(approval.payload.output)) body = { output: corrected };
      } catch {
        return action.setError(t("appr.badJson"));
      }
    }

    const done = await action.run(() =>
      api(`${base}/approvals/${approval.id}/${approve ? "approve" : "reject"}`, { body }),
    );
    if (done !== undefined) onDecided();
  }

  return (
    <div ref={cardRef} className={`scroll-mt-4 rounded-xl ${focused ? "ring-2 ring-indigo-500" : ""}`}>
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="font-semibold">{title(approval, t)}</h2>
          <p className="text-xs text-slate-500">
            {approval.customer_email && <>{approval.customer_email} · </>}
            {formatTime(approval.created_at)}
            {approval.execution_id && (
              <>
                {" · "}
                <Link href={`/executions/${approval.execution_id}`} className="hover:text-indigo-600">
                  {t("appr.run", { id: approval.execution_id })}
                </Link>
              </>
            )}
          </p>
        </div>
        <StatusBadge status={approval.status} />
      </div>

      {isReview && (
        <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">{approval.payload.reason}</p>
      )}

      {approval.kind === "classification" && (
        <div className="mt-3 space-y-2 text-sm">
          <p className="rounded-lg bg-slate-50 p-3 italic text-slate-700">“{approval.payload.message}”</p>
          <p>
            {t("appr.aiSays")} <strong>{approval.payload.suggested_category}</strong>: {approval.payload.reason}
          </p>
          {pending && (
            <label className="flex items-center gap-2">
              {t("appr.category")}
              <select className={`${inputClass} w-auto`} value={category} onChange={(e) => setCategory(e.target.value)}>
                {["Sales", "Support", "Other"].map((option) => <option key={option}>{option}</option>)}
              </select>
            </label>
          )}
        </div>
      )}

      {email && looksLikeEmail && !isReview && (
        <div className="mt-3 rounded-lg border border-slate-200 text-sm">
          <p className="border-b border-slate-200 px-3 py-2"><span className="text-slate-500">{t("appr.to")}</span> {String(email.to)}</p>
          <p className="border-b border-slate-200 px-3 py-2"><span className="text-slate-500">{t("appr.subject")}</span> {String(email.subject)}</p>
          <p className="whitespace-pre-wrap px-3 py-2">{String(email.body)}</p>
        </div>
      )}

      {approval.kind === "step" && !looksLikeEmail && !isReview && (
        <div className="mt-3"><JsonBlock value={approval.payload.inputs} /></div>
      )}

      {isReview && (
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <div>
            <p className="mb-1 text-xs font-medium uppercase text-slate-500">{t("appr.whatAiRead")}</p>
            <JsonBlock value={approval.payload.inputs} />
          </div>
          <div>
            <p className="mb-1 text-xs font-medium uppercase text-slate-500">
              {pending ? t("appr.resultEdit") : t("appr.result")}
            </p>
            {pending ? (
              <textarea
                className={`${inputClass} min-h-48 font-mono text-xs`}
                value={output}
                onChange={(e) => setOutput(e.target.value)}
                spellCheck={false}
              />
            ) : (
              <JsonBlock value={approval.payload.output} />
            )}
          </div>
        </div>
      )}

      <ErrorNote message={action.error} />

      {pending && can("member") && (
        <div className="mt-4 flex gap-2">
          {/* Large tap targets on phones */}
          <Button className="flex-1 py-3 sm:flex-none sm:py-2" onClick={() => decide(true)} disabled={action.busy}>
            {isReview ? t("appr.accept") : t("appr.approve")}
          </Button>
          <Button variant="secondary" className="flex-1 py-3 sm:flex-none sm:py-2" onClick={() => decide(false)} disabled={action.busy}>
            {t("appr.reject")}
          </Button>
        </div>
      )}
    </Card>
    </div>
  );
}
