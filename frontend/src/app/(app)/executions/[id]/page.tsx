"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { Button, Card, ErrorNote, JsonBlock, Loading, StatusBadge, formatTime } from "@/components/ui";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";
import type { Execution } from "@/lib/types";
import { useAction, useApi } from "@/lib/useApi";

const OPEN = new Set(["queued", "running", "waiting_approval"]);

export default function ExecutionPage() {
  const { id } = useParams<{ id: string }>();
  const { base, can } = useSession();
  const { data: execution, error, loading, setData } = useApi<Execution>(`${base}/executions/${id}`);
  const action = useAction();

  if (loading && !execution) return <Loading />;
  if (error) return <ErrorNote message={error} />;
  if (!execution) return null;

  async function operate(path: string, body?: unknown, confirmText?: string) {
    if (confirmText && !window.confirm(confirmText)) return;
    const updated = await action.run(() => api<Execution>(`${base}/executions/${id}/${path}`, { body: body ?? {} }));
    if (updated) setData(updated);
  }

  return (
    <>
      <Link href="/executions" className="text-sm text-slate-500 hover:text-slate-800">← Run history</Link>
      <div className="mt-1 mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Run #{execution.id}</h1>
          <p className="mt-1 text-sm text-slate-500">
            <Link href={`/workflows/${execution.workflow_id}`} className="hover:text-indigo-600">Open workflow</Link>
            {" · "}{execution.mode} run · started {formatTime(execution.started_at ?? execution.created_at)}
            {execution.finished_at && <> · finished {formatTime(execution.finished_at)}</>}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={execution.status} />
          {can("member") && OPEN.has(execution.status) && (
            <Button variant="danger" disabled={action.busy} onClick={() => operate("cancel", undefined, "Cancel this run?")}>
              Cancel run
            </Button>
          )}
          {can("member") && execution.status === "failed" && (
            <Button disabled={action.busy} onClick={() => operate("retry")}>Retry from failed step</Button>
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
              I checked — retry
            </Button>
          )}
        </div>
      </div>

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

      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <h2 className="font-semibold">Trigger data</h2>
          <div className="mt-3"><JsonBlock value={execution.trigger_payload} /></div>
        </Card>

        <div className="space-y-3 lg:col-span-2">
          {execution.steps.map((step) => (
            <Card key={step.step_id}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <span className="text-xs text-slate-400">Step {step.position + 1}</span>
                  <h3 className="font-semibold">{step.step_id}</h3>
                  <code className="text-xs text-slate-500">{step.action}</code>
                </div>
                <div className="text-right text-xs text-slate-500">
                  <StatusBadge status={step.status} />
                  <p className="mt-1">{step.attempts} attempt(s)</p>
                </div>
              </div>
              {step.error && <p className="mt-2 text-sm text-red-700">{step.error}</p>}
              {(step.input || step.output) && (
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  {step.input && (
                    <div>
                      <p className="mb-1 text-xs font-medium uppercase text-slate-500">Input</p>
                      <JsonBlock value={step.input} />
                    </div>
                  )}
                  {step.output && (
                    <div>
                      <p className="mb-1 text-xs font-medium uppercase text-slate-500">Output</p>
                      <JsonBlock value={step.output} />
                    </div>
                  )}
                </div>
              )}
            </Card>
          ))}
        </div>
      </div>
    </>
  );
}
