"use client";

import { useSearchParams } from "next/navigation";

import { Button, Card, ErrorNote, Loading, PageHeader, StatusBadge, formatTime } from "@/components/ui";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";
import { useAction, useApi } from "@/lib/useApi";

interface Plan {
  name: string;
  label: string;
  price_usd_month: number | null;
  included_tasks: number | null;
  max_workflows: number | null;
  max_seats: number | null;
  description: string;
}

interface Billing {
  plan: Plan;
  status: string;
  provider: string;
  cancel_at_period_end: boolean;
  hard_cap: boolean;
  period: { start: string; end: string };
  usage: { billable_tasks: number; included_tasks: number | null; projected_tasks: number };
  limits: { workflows: { used: number; max: number | null }; seats: { used: number; max: number | null } };
  alerts: string[];
  online_payments: boolean;
}

const unlimited = (value: number | null) => (value === null ? "Unlimited" : value.toLocaleString());

export default function BillingPage() {
  const { base, workspace } = useSession();
  const searchParams = useSearchParams();
  const { data, error, loading, reload } = useApi<Billing>(`${base}/billing`);
  const { data: plans } = useApi<Plan[]>("/plans");
  const action = useAction();

  if (loading && !data) return <Loading />;
  if (!data) return <ErrorNote message={error} />;

  const included = data.usage.included_tasks;
  const share = included ? Math.min(100, Math.round((data.usage.billable_tasks / included) * 100)) : 0;
  // Billing changes are reserved for the workspace owner
  const owner = workspace.role === "owner";

  async function redirect(path: string, body?: unknown) {
    const result = await action.run(() => api<{ url: string }>(`${base}/billing/${path}`, { body: body ?? {} }));
    if (result) window.location.href = result.url;
  }

  return (
    <>
      <PageHeader
        title="Plan & usage"
        description="You pay for tasks that work: a step that succeeds and calls an app or AI. Failed steps, retries and test runs are free."
      />

      {searchParams.get("checkout") === "success" && (
        <p className="mb-4 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          Thanks! Your plan updates as soon as the payment is confirmed.
        </p>
      )}
      {data.alerts.map((alert) => (
        <p key={alert} className="mb-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">{alert}</p>
      ))}
      <ErrorNote message={action.error} />

      <div className="grid gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <p className="text-sm text-slate-500">Current plan</p>
              <p className="text-2xl font-semibold">{data.plan.label}</p>
              <p className="text-sm text-slate-500">
                {formatTime(data.period.start)} – {formatTime(data.period.end)}
                {data.cancel_at_period_end && " · ends at period end"}
              </p>
            </div>
            <StatusBadge status={data.status} />
          </div>

          <div className="mt-6">
            <div className="flex justify-between text-sm">
              <span>Tasks this period</span>
              <span className="tabular-nums text-slate-600">
                {data.usage.billable_tasks.toLocaleString()} / {unlimited(included)}
              </span>
            </div>
            {included !== null && (
              <div className="mt-1 h-3 rounded-full bg-slate-100">
                <div className={`h-3 rounded-full ${share >= 90 ? "bg-red-500" : "bg-indigo-500"}`} style={{ width: `${share}%` }} />
              </div>
            )}
            <p className="mt-2 text-xs text-slate-500">
              Projected for the full period: about {data.usage.projected_tasks.toLocaleString()} tasks.
              {included !== null && (data.hard_cap ? " Billable steps pause at the limit." : " Usage can go over the limit.")}
            </p>
          </div>

          <dl className="mt-6 grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-slate-500">Workflows</dt>
              <dd className="font-medium">{data.limits.workflows.used} / {unlimited(data.limits.workflows.max)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Seats</dt>
              <dd className="font-medium">{data.limits.seats.used} / {unlimited(data.limits.seats.max)}</dd>
            </div>
          </dl>

          {owner && data.provider === "stripe" && (
            <Button variant="secondary" className="mt-6" disabled={action.busy} onClick={() => redirect("portal")}>
              Manage payment & invoices
            </Button>
          )}
          {owner && data.plan.name !== "free" && (
            <label className="mt-4 flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={data.hard_cap}
                onChange={async (event) => {
                  await action.run(() =>
                    api(`${base}/billing`, { method: "PATCH", body: { hard_cap: event.target.checked } }),
                  );
                  reload();
                }}
              />
              Pause billable steps when included tasks run out
            </label>
          )}
        </Card>

        <Card>
          <h2 className="font-semibold">Need more?</h2>
          <p className="mt-1 text-sm text-slate-500">
            {data.online_payments
              ? "Upgrade any time; changes take effect right after payment."
              : "Online payments are not enabled yet. Contact us to change plans (pilot invoicing)."}
          </p>
        </Card>
      </div>

      <h2 className="mt-8 mb-3 font-semibold">Plans</h2>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {plans?.map((plan) => {
          const current = plan.name === data.plan.name;
          return (
            <Card key={plan.name} className={current ? "border-indigo-400 ring-1 ring-indigo-400" : ""}>
              <p className="font-semibold">{plan.label}</p>
              <p className="mt-1 text-2xl font-semibold">
                {plan.price_usd_month === null ? "Custom" : `$${plan.price_usd_month}`}
                {plan.price_usd_month ? <span className="text-sm font-normal text-slate-500">/mo</span> : null}
              </p>
              <p className="mt-1 text-xs text-slate-500">{plan.description}</p>
              <ul className="mt-3 space-y-1 text-sm text-slate-600">
                <li>{unlimited(plan.included_tasks)} tasks/month</li>
                <li>{unlimited(plan.max_workflows)} workflows</li>
                <li>{unlimited(plan.max_seats)} seat{plan.max_seats === 1 ? "" : "s"}</li>
              </ul>
              {current ? (
                <p className="mt-4 text-sm font-medium text-indigo-700">Your plan</p>
              ) : owner && data.online_payments && plan.price_usd_month ? (
                <Button className="mt-4 w-full" disabled={action.busy} onClick={() => redirect("checkout", { plan: plan.name })}>
                  Choose {plan.label}
                </Button>
              ) : null}
            </Card>
          );
        })}
      </div>
    </>
  );
}
