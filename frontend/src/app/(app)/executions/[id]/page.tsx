"use client";

import {
  AlertTriangle,
  CheckCircle2,
  CircleDashed,
  Clock,
  Loader2,
  type LucideIcon,
  MinusCircle,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { Button, Card, ErrorNote, JsonBlock, Loading, StatusBadge, TechnicalDetails, formatTime } from "@/components/ui";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";
import { type MessageKey, useI18n } from "@/lib/i18n";
import type { ActionInfo, Execution, StepExecution } from "@/lib/types";
import { useAction, useApi } from "@/lib/useApi";

const OPEN = new Set(["queued", "running", "waiting_approval"]);

const STEP_ICONS: Record<string, { icon: LucideIcon; className: string }> = {
  succeeded: { icon: CheckCircle2, className: "text-emerald-600" },
  failed: { icon: XCircle, className: "text-red-600" },
  needs_attention: { icon: AlertTriangle, className: "text-orange-600" },
  waiting_approval: { icon: Clock, className: "text-amber-600" },
  running: { icon: Loader2, className: "animate-spin text-blue-600" },
  skipped: { icon: MinusCircle, className: "text-slate-400" },
  cancelled: { icon: MinusCircle, className: "text-slate-400" },
};

/** "send_invoice_email" -> "Send invoice email" */
function humanize(id: string) {
  const words = id.replaceAll("_", " ").replaceAll("-", " ").trim();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/** Top-level simple values of the trigger data, for a readable summary. */
function summaryFields(payload: Record<string, unknown>) {
  return Object.entries(payload)
    .filter(([, value]) => ["string", "number", "boolean"].includes(typeof value) && String(value).length <= 120)
    .slice(0, 8);
}

export default function ExecutionPage() {
  const { id } = useParams<{ id: string }>();
  const { base, can } = useSession();
  const { t } = useI18n();
  const { data: execution, error, loading, setData } = useApi<Execution>(`${base}/executions/${id}`);
  const { data: actions } = useApi<ActionInfo[]>("/actions");
  const action = useAction();

  if (loading && !execution) return <Loading />;
  if (error) return <ErrorNote message={error} />;
  if (!execution) return null;

  const descriptions = new Map(actions?.map((item) => [item.name, item.description]));
  const summaryKey = `ex.summary.${execution.status}` as MessageKey;
  const summary = t(summaryKey);
  const fields = summaryFields(execution.trigger_payload);

  async function operate(path: string, body?: unknown, confirmText?: string) {
    if (confirmText && !window.confirm(confirmText)) return;
    const updated = await action.run(() => api<Execution>(`${base}/executions/${id}/${path}`, { body: body ?? {} }));
    if (updated) setData(updated);
  }

  return (
    <>
      <Link href="/executions" className="text-sm text-slate-500 hover:text-slate-800">{t("ex.back")}</Link>
      <div className="mt-1 mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">{t("ex.title", { id: execution.id })}</h1>
          <p className="mt-1 text-sm text-slate-500">
            <Link href={`/workflows/${execution.workflow_id}`} className="hover:text-brand-600">{t("ex.openWorkflow")}</Link>
            {" · "}{execution.mode === "live" ? t("ex.liveMode") : t("ex.testMode")}
            {" · "}{t("ex.started", { time: formatTime(execution.started_at ?? execution.created_at) })}
            {execution.finished_at && <> · {t("ex.finished", { time: formatTime(execution.finished_at) })}</>}
            {execution.ai_calls ? (
              <> · {t("ex.aiCost", { calls: execution.ai_calls, cost: `$${(execution.ai_cost_usd ?? 0).toFixed(2)}` })}</>
            ) : null}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={execution.status} />
          {can("member") && OPEN.has(execution.status) && (
            <Button variant="danger" disabled={action.busy} onClick={() => operate("cancel", undefined, "Cancel this run?")}>
              {t("ex.cancel")}
            </Button>
          )}
          {can("member") && execution.status === "failed" && (
            <Button disabled={action.busy} onClick={() => operate("retry")}>{t("ex.retry")}</Button>
          )}
          {can("member") && execution.status === "needs_attention" && (
            <Button
              disabled={action.busy}
              onClick={() =>
                operate(
                  "retry",
                  { confirm_not_completed: true },
                  "Only retry if you have checked that the uncertain step did NOT happen (for example, the email was not received). Retry now?",
                )
              }
            >
              {t("ex.checkedRetry")}
            </Button>
          )}
        </div>
      </div>

      {summary !== summaryKey && <p className="mb-4 text-sm text-slate-700">{summary}</p>}
      <ErrorNote message={action.error ?? execution.error} />
      {execution.status === "queued" && execution.run_after && (
        <p className="mb-4 rounded-lg bg-blue-50 px-3 py-2 text-sm text-blue-900">
          Waiting on a delay step. Resumes {formatTime(execution.run_after)}.
        </p>
      )}
      {execution.status === "waiting_approval" && (
        <p className="mb-4 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">
          This run is waiting for a decision. <Link href="/approvals" className="underline">Go to approvals</Link>
        </p>
      )}

      <div className="mt-4 grid gap-6 lg:grid-cols-3">
        <Card>
          <h2 className="font-semibold">{t("ex.what")}</h2>
          {fields.length > 0 && (
            <dl className="mt-3 space-y-2 text-sm">
              {fields.map(([key, value]) => (
                <div key={key}>
                  <dt className="text-xs text-slate-500">{humanize(key)}</dt>
                  <dd className="break-words text-slate-800">{String(value)}</dd>
                </div>
              ))}
            </dl>
          )}
          <TechnicalDetails label={t("ex.trigger")}>
            <JsonBlock value={execution.trigger_payload} />
          </TechnicalDetails>
        </Card>

        <ol className="space-y-3 lg:col-span-2">
          {execution.steps.map((step) => (
            <StepCard key={step.step_id} step={step} description={descriptions.get(step.action)} />
          ))}
        </ol>
      </div>
    </>
  );
}

function StepCard({ step, description }: { step: StepExecution; description?: string }) {
  const { t } = useI18n();
  const { icon: Icon, className } = STEP_ICONS[step.status] ?? { icon: CircleDashed, className: "text-slate-400" };

  return (
    <li>
      <Card>
        <div className="flex items-start gap-3">
          <Icon aria-hidden className={`mt-0.5 size-5 shrink-0 ${className}`} />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="text-xs text-slate-400">{t("ex.step", { n: step.position + 1 })}</p>
                <h3 className="font-semibold">{humanize(step.step_id)}</h3>
                <p className="text-sm text-slate-500">{description ?? humanize(step.action)}</p>
              </div>
              <div className="text-right text-xs text-slate-500">
                <StatusBadge status={step.status} />
                {step.attempts > 1 && <p className="mt-1">{t("ex.tries", { n: step.attempts })}</p>}
              </div>
            </div>
            {step.error && (
              <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-800">{step.error}</p>
            )}
            {Array.isArray(step.output?.safety_warnings) && (
              <div className="mt-3 rounded-lg bg-orange-50 px-3 py-2 text-sm text-orange-900">
                <p className="font-medium">{t("ex.safety")}</p>
                <ul className="mt-1 list-disc pl-5">
                  {(step.output.safety_warnings as string[]).map((warning) => <li key={warning}>{warning}</li>)}
                </ul>
              </div>
            )}
            {(step.input || step.output) && (
              <TechnicalDetails>
                <div className="grid gap-3 md:grid-cols-2">
                  {step.input && (
                    <div>
                      <p className="mb-1 text-xs font-medium uppercase text-slate-500">{t("ex.input")}</p>
                      <JsonBlock value={step.input} />
                    </div>
                  )}
                  {step.output && (
                    <div>
                      <p className="mb-1 text-xs font-medium uppercase text-slate-500">{t("ex.output")}</p>
                      <JsonBlock value={step.output} />
                    </div>
                  )}
                </div>
                <p className="mt-2 text-xs text-slate-400">
                  <code>{step.action}</code> · <code>{step.step_id}</code>
                </p>
              </TechnicalDetails>
            )}
          </div>
        </div>
      </Card>
    </li>
  );
}
