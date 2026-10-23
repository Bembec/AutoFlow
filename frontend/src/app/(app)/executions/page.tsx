"use client";

import { History } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { EmptyState, ErrorNote, Loading, PageHeader, StatusBadge, formatTime } from "@/components/ui";
import { useSession } from "@/lib/session";
import { useI18n } from "@/lib/i18n";
import type { Execution, Workflow } from "@/lib/types";
import { useApi } from "@/lib/useApi";

const FILTERS = ["all", "waiting_approval", "failed", "needs_attention", "succeeded", "cancelled"] as const;

export default function ExecutionsPage() {
  const { base } = useSession();
  const { t } = useI18n();
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("all");
  const query = filter === "all" ? "" : `&status=${filter}`;
  const { data, error, loading } = useApi<Execution[]>(`${base}/executions?limit=100${query}`);
  const { data: workflows } = useApi<Workflow[]>(`${base}/workflows?include_archived=true`);
  const names = new Map(workflows?.map((w) => [w.id, w.name]));

  return (
    <>
      <PageHeader title={t("runs.title")} description={t("runs.subtitle")} />
      <div className="mb-4 flex flex-wrap gap-2">
        {FILTERS.map((item) => (
          <button
            key={item}
            onClick={() => setFilter(item)}
            aria-pressed={filter === item}
            className={`rounded-full px-3 py-1 text-sm ${filter === item ? "bg-brand-600 text-white" : "bg-white text-slate-600 ring-1 ring-slate-200"}`}
          >
            {item === "all" ? t("ui.all") : t(`status.${item}`)}
          </button>
        ))}
      </div>
      <ErrorNote message={error} />
      {loading && !data ? (
        <Loading />
      ) : data && data.length === 0 ? (
        <EmptyState icon={History} title={t("runs.empty")} />
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">{t("col.run")}</th>
                <th className="px-4 py-3 font-medium">{t("col.workflow")}</th>
                <th className="hidden px-4 py-3 font-medium sm:table-cell">{t("col.mode")}</th>
                <th className="hidden px-4 py-3 font-medium md:table-cell">{t("col.started")}</th>
                <th className="px-4 py-3 font-medium">{t("col.status")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.map((execution) => (
                <tr key={execution.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link href={`/executions/${execution.id}`} className="font-medium text-brand-600 hover:underline">
                      #{execution.id}
                    </Link>
                  </td>
                  <td className="px-4 py-3">{names.get(execution.workflow_id) ?? `Workflow ${execution.workflow_id}`}</td>
                  <td className="hidden px-4 py-3 text-slate-500 sm:table-cell">{execution.mode}</td>
                  <td className="hidden px-4 py-3 text-slate-500 md:table-cell">{formatTime(execution.created_at)}</td>
                  <td className="px-4 py-3"><StatusBadge status={execution.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
