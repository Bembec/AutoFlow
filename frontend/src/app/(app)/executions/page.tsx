"use client";

import Link from "next/link";
import { useState } from "react";

import { EmptyState, ErrorNote, Loading, PageHeader, StatusBadge, formatTime } from "@/components/ui";
import { useSession } from "@/lib/session";
import type { Execution, Workflow } from "@/lib/types";
import { useApi } from "@/lib/useApi";

const FILTERS = ["all", "waiting_approval", "failed", "needs_attention", "succeeded", "cancelled"] as const;

export default function ExecutionsPage() {
  const { base } = useSession();
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("all");
  const query = filter === "all" ? "" : `&status=${filter}`;
  const { data, error, loading } = useApi<Execution[]>(`${base}/executions?limit=100${query}`);
  const { data: workflows } = useApi<Workflow[]>(`${base}/workflows?include_archived=true`);
  const names = new Map(workflows?.map((w) => [w.id, w.name]));

  return (
    <>
      <PageHeader title="Run history" description="Every run, step by step. Failed runs can be retried from the step that failed." />
      <div className="mb-4 flex flex-wrap gap-2">
        {FILTERS.map((item) => (
          <button
            key={item}
            onClick={() => setFilter(item)}
            className={`rounded-full px-3 py-1 text-sm ${filter === item ? "bg-indigo-600 text-white" : "bg-white text-slate-600 ring-1 ring-slate-200"}`}
          >
            {item.replaceAll("_", " ")}
          </button>
        ))}
      </div>
      <ErrorNote message={error} />
      {loading && !data ? (
        <Loading />
      ) : data && data.length === 0 ? (
        <EmptyState title="No runs here" />
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">Run</th>
                <th className="px-4 py-3 font-medium">Workflow</th>
                <th className="hidden px-4 py-3 font-medium sm:table-cell">Mode</th>
                <th className="hidden px-4 py-3 font-medium md:table-cell">Started</th>
                <th className="px-4 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.map((execution) => (
                <tr key={execution.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link href={`/executions/${execution.id}`} className="font-medium text-indigo-600 hover:underline">
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
