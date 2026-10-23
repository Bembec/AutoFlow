"use client";

import { BarChart3 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { SuggestionList } from "@/components/Suggestions";
import { Button, Card, EmptyState, ErrorNote, Field, Loading, PageHeader, StatusBadge, formatMinutes, inputClass } from "@/components/ui";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { useSession } from "@/lib/session";
import type { Insights } from "@/lib/types";
import { useAction, useApi } from "@/lib/useApi";

const CURRENCIES = ["USD", "EUR", "GBP", "CAD", "AUD", "CHF", "TRY", "NGN", "ZAR", "INR", "JPY", "BRL", "MXN"];

function useMoney() {
  const { language } = useI18n();
  return (value: number | null, currency: string) =>
    value === null
      ? "—"
      : new Intl.NumberFormat(language, { style: "currency", currency, maximumFractionDigits: value >= 100 ? 0 : 2 }).format(value);
}

function Stat({ label, value, hint }: { label: string; value: React.ReactNode; hint?: React.ReactNode }) {
  return (
    <Card>
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">{value}</p>
      {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
    </Card>
  );
}

export default function InsightsPage() {
  const { base } = useSession();
  const { t } = useI18n();
  const money = useMoney();
  const { data, error, loading, setData } = useApi<Insights>(`${base}/insights`);

  if (loading && !data) return <Loading />;
  if (!data) return <ErrorNote message={error} />;

  const month = data.last_30_days;
  const currency = data.time_value.currency;
  const peak = Math.max(...data.weekly_minutes_saved, 1);

  return (
    <>
      <PageHeader title={t("nav.insights")} description={t("ins.subtitle")} />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label={t("ins.time")} value={formatMinutes(month.minutes_saved)} />
        <Stat
          label={t("ins.money")}
          value={money(month.money_saved, currency)}
          hint={data.time_value.per_hour === null ? t("ins.setRate") : undefined}
        />
        <Stat label={t("ins.runs")} value={month.live_runs.toLocaleString()} />
        <Stat
          label={t("ins.success")}
          value={month.success_rate === null ? "—" : `${Math.round(month.success_rate * 100)}%`}
        />
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-3">
        <div className="space-y-6 xl:col-span-2">
          <Card>
            <h2 className="font-semibold">{t("ins.trend")}</h2>
            {month.live_runs === 0 && data.weekly_minutes_saved.every((minutes) => minutes === 0) ? (
              <p className="mt-3 text-sm text-slate-500">{t("ins.empty")}</p>
            ) : (
              <div className="mt-4">
                <div className="flex h-40 items-end gap-2" role="img" aria-label={t("ins.trend")}>
                  {data.weekly_minutes_saved.map((minutes, index) => (
                    <div key={index} className="flex h-full flex-1 flex-col justify-end" title={formatMinutes(minutes)}>
                      <div
                        className={`rounded-t-md ${index === data.weekly_minutes_saved.length - 1 ? "bg-brand-600" : "bg-brand-300"}`}
                        style={{ height: `${Math.max(2, (minutes / peak) * 100)}%` }}
                      />
                    </div>
                  ))}
                </div>
                <div className="mt-2 flex justify-between text-xs text-slate-500">
                  <span>{t("ins.weeksAgo", { n: data.weekly_minutes_saved.length - 1 })}</span>
                  <span>{t("ins.thisWeek")}</span>
                </div>
              </div>
            )}
          </Card>

          <Card className="overflow-hidden p-0">
            <h2 className="px-5 pt-5 font-semibold">{t("ins.byWorkflow")}</h2>
            {data.per_workflow.length === 0 ? (
              <div className="p-5">
                <EmptyState icon={BarChart3} title={t("wf.empty")} />
              </div>
            ) : (
              <div className="mt-3 overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="px-5 py-3 font-medium">{t("col.workflow")}</th>
                      <th className="px-5 py-3 text-right font-medium">{t("ins.colRuns")}</th>
                      <th className="px-5 py-3 text-right font-medium">{t("ins.colTime")}</th>
                      <th className="hidden px-5 py-3 text-right font-medium sm:table-cell">{t("ins.colValue")}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {data.per_workflow.map((row) => (
                      <tr key={row.id}>
                        <td className="px-5 py-3">
                          <Link href={`/workflows/${row.id}`} className="font-medium text-slate-900 hover:text-brand-600">
                            {row.name}
                          </Link>
                          <span className="ml-2 align-middle"><StatusBadge status={row.status} /></span>
                        </td>
                        <td className="px-5 py-3 text-right tabular-nums">{row.runs_30d}</td>
                        <td className="px-5 py-3 text-right tabular-nums">{formatMinutes(row.minutes_saved_30d)}</td>
                        <td className="hidden px-5 py-3 text-right tabular-nums sm:table-cell">{money(row.money_saved_30d, currency)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>

        <div className="space-y-6">
          <section>
            <h2 className="mb-3 font-semibold">{t("ins.next")}</h2>
            <SuggestionList suggestions={data.suggestions} />
          </section>
          <TimeValueCard insights={data} onSaved={setData} />
        </div>
      </div>
    </>
  );
}

function TimeValueCard({ insights, onSaved }: { insights: Insights; onSaved: (insights: Insights) => void }) {
  const { base, can } = useSession();
  const { t } = useI18n();
  const action = useAction();
  const [perHour, setPerHour] = useState(insights.time_value.per_hour?.toString() ?? "");
  const [currency, setCurrency] = useState(insights.time_value.currency);

  if (!can("admin")) return null;

  return (
    <Card>
      <form
        className="space-y-3"
        onSubmit={async (event) => {
          event.preventDefault();
          const updated = await action.run(() =>
            api<Insights>(`${base}/insights/time-value`, {
              method: "PUT",
              body: { per_hour: perHour.trim() === "" ? null : Number(perHour), currency },
            }),
          );
          if (updated) onSaved(updated);
        }}
      >
        <div className="grid grid-cols-[1fr_auto] gap-3">
          <Field label={t("ins.rateLabel")}>
            <input
              className={inputClass}
              type="number"
              min={0}
              step="any"
              inputMode="decimal"
              value={perHour}
              onChange={(event) => setPerHour(event.target.value)}
            />
          </Field>
          <Field label={t("ins.currency")}>
            <select className={inputClass} value={currency} onChange={(event) => setCurrency(event.target.value)}>
              {[...new Set([currency, ...CURRENCIES])].map((code) => <option key={code}>{code}</option>)}
            </select>
          </Field>
        </div>
        <ErrorNote message={action.error} />
        <Button type="submit" variant="secondary" disabled={action.busy}>{t("common.save")}</Button>
      </form>
    </Card>
  );
}
