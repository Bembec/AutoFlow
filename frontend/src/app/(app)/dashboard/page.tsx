"use client";

import Link from "next/link";

import { Card, EmptyState, ErrorNote, LinkButton, Loading, PageHeader, StatusBadge, formatMinutes, formatTime } from "@/components/ui";
import { useSession } from "@/lib/session";
import type { Dashboard } from "@/lib/types";
import { useApi } from "@/lib/useApi";

function Stat({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <Card>
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-900">{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </Card>
  );
}

function Meter({ label, used, limit }: { label: string; used: number; limit: number }) {
  const share = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 100;
  return (
    <div>
      <div className="flex justify-between text-sm">
        <span className="text-slate-600">{label}</span>
        <span className="tabular-nums text-slate-500">
          {used} / {limit}
        </span>
      </div>
      <div className="mt-1 h-2 rounded-full bg-slate-100">
        <div
          className={`h-2 rounded-full ${share >= 90 ? "bg-red-500" : "bg-indigo-500"}`}
          style={{ width: `${share}%` }}
        />
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { base, workspace } = useSession();
  const { data, error, loading } = useApi<Dashboard>(`${base}/dashboard`);

  if (loading && !data) return <Loading />;
  if (error) return <ErrorNote message={error} />;
  if (!data) return null;

  const today = Object.values(data.executions_today).reduce((sum, n) => sum + (n ?? 0), 0);

  return (
    <>
      <PageHeader
        title={workspace.name}
        description="What your automations did for you."
        actions={<LinkButton href="/workflows/new">New workflow</LinkButton>}
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Time saved (30 days)" value={formatMinutes(data.minutes_saved_30d)} hint="Successful live runs × minutes per run" />
        <Stat label="Runs today" value={today} hint={`${data.executions_today.failed ?? 0} failed`} />
        <Stat
          label="Waiting for you"
          value={<Link href="/approvals" className="hover:text-indigo-600">{data.pending_approvals}</Link>}
          hint="Approvals and reviews"
        />
        <Stat label="Workflows" value={data.workflows.total} hint={`${data.workflows.active} active · ${data.workflows.paused} paused`} />
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <h2 className="font-semibold">Recent runs</h2>
          {data.recent_executions.length === 0 ? (
            <div className="mt-4">
              <EmptyState title="No runs yet">Open a workflow and press “Test run” to see it work step by step.</EmptyState>
            </div>
          ) : (
            <ul className="mt-3 divide-y divide-slate-100">
              {data.recent_executions.map((execution) => (
                <li key={execution.id}>
                  <Link
                    href={`/executions/${execution.id}`}
                    className="flex flex-wrap items-center justify-between gap-2 py-2.5 hover:bg-slate-50"
                  >
                    <span className="min-w-0">
                      <span className="font-medium">{execution.workflow_name}</span>
                      <span className="ml-2 text-xs text-slate-500">
                        #{execution.id} · {execution.mode} · {formatTime(execution.created_at)}
                      </span>
                    </span>
                    <StatusBadge status={execution.status} />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <div className="space-y-6">
          <Card>
            <h2 className="font-semibold">Today’s limits</h2>
            <div className="mt-4 space-y-4">
              <Meter label="Runs" used={data.usage_today.executions} limit={data.limits.executions} />
              <Meter label="AI calls" used={data.usage_today.ai_calls} limit={data.limits.ai_calls} />
              <Meter label="Emails sent" used={data.usage_today.emails} limit={data.limits.emails} />
            </div>
          </Card>

          <Card>
            <h2 className="font-semibold">Time saved by workflow</h2>
            {data.per_workflow.length === 0 ? (
              <p className="mt-3 text-sm text-slate-500">No workflows yet.</p>
            ) : (
              <ul className="mt-3 space-y-2 text-sm">
                {data.per_workflow.map((item) => (
                  <li key={item.id} className="flex justify-between gap-2">
                    <Link href={`/workflows/${item.id}`} className="truncate hover:text-indigo-600">
                      {item.name}
                    </Link>
                    <span className="shrink-0 tabular-nums text-slate-500">
                      {formatMinutes(item.minutes_saved_30d)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}
