"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Button, Card, EmptyState, ErrorNote, JsonBlock, Loading, PageHeader, StatusBadge, formatTime, inputClass } from "@/components/ui";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";
import type { Approval } from "@/lib/types";
import { useAction, useApi } from "@/lib/useApi";

export default function ApprovalsPage() {
  const { base } = useSession();
  const [view, setView] = useState<"pending" | "history">("pending");
  const path = view === "pending" ? `${base}/approvals?status=pending` : `${base}/approvals`;
  const { data, error, loading, reload } = useApi<Approval[]>(path);
  const items = view === "history" ? data?.filter((a) => a.status !== "pending") : data;
  // Notification links open one approval: /approvals?focus=<id>
  const focus = Number(useSearchParams().get("focus")) || null;

  return (
    <>
      <PageHeader
        title="Approvals"
        description="Anything sensitive waits here for a person: emails to customers, unsure AI results, and possible prompt-injection attempts."
      />
      <div className="mb-4 flex gap-2">
        {(["pending", "history"] as const).map((item) => (
          <button
            key={item}
            onClick={() => setView(item)}
            className={`rounded-full px-3 py-1 text-sm ${view === item ? "bg-indigo-600 text-white" : "bg-white text-slate-600 ring-1 ring-slate-200"}`}
          >
            {item === "pending" ? "Waiting" : "Decided"}
          </button>
        ))}
      </div>
      <ErrorNote message={error} />
      {loading && !data ? (
        <Loading />
      ) : !items || items.length === 0 ? (
        <EmptyState title={view === "pending" ? "Nothing waiting for you" : "No decisions yet"} />
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

function title(approval: Approval) {
  if (approval.kind === "classification") return "Check the AI’s category";
  if (approval.kind === "email") return "Send this email?";
  if (approval.payload.review) return `Review AI result: ${approval.payload.step_name}`;
  return `Approve step: ${approval.payload.step_name}`;
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
        return action.setError("The corrected result is not valid JSON.");
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
          <h2 className="font-semibold">{title(approval)}</h2>
          <p className="text-xs text-slate-500">
            {approval.customer_email && <>{approval.customer_email} · </>}
            {formatTime(approval.created_at)}
            {approval.execution_id && (
              <>
                {" · "}
                <Link href={`/executions/${approval.execution_id}`} className="hover:text-indigo-600">
                  run #{approval.execution_id}
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
            AI says <strong>{approval.payload.suggested_category}</strong>: {approval.payload.reason}
          </p>
          {pending && (
            <label className="flex items-center gap-2">
              Category
              <select className={`${inputClass} w-auto`} value={category} onChange={(e) => setCategory(e.target.value)}>
                {["Sales", "Support", "Other"].map((option) => <option key={option}>{option}</option>)}
              </select>
            </label>
          )}
        </div>
      )}

      {email && looksLikeEmail && !isReview && (
        <div className="mt-3 rounded-lg border border-slate-200 text-sm">
          <p className="border-b border-slate-200 px-3 py-2"><span className="text-slate-500">To:</span> {String(email.to)}</p>
          <p className="border-b border-slate-200 px-3 py-2"><span className="text-slate-500">Subject:</span> {String(email.subject)}</p>
          <p className="whitespace-pre-wrap px-3 py-2">{String(email.body)}</p>
        </div>
      )}

      {approval.kind === "step" && !looksLikeEmail && !isReview && (
        <div className="mt-3"><JsonBlock value={approval.payload.inputs} /></div>
      )}

      {isReview && (
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <div>
            <p className="mb-1 text-xs font-medium uppercase text-slate-500">What the AI read</p>
            <JsonBlock value={approval.payload.inputs} />
          </div>
          <div>
            <p className="mb-1 text-xs font-medium uppercase text-slate-500">
              {pending ? "Result (correct it if needed)" : "Result"}
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
            {isReview ? "Accept and continue" : "Approve"}
          </Button>
          <Button variant="secondary" className="flex-1 py-3 sm:flex-none sm:py-2" onClick={() => decide(false)} disabled={action.busy}>
            Reject
          </Button>
        </div>
      )}
    </Card>
    </div>
  );
}
