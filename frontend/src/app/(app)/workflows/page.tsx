"use client";

import { Workflow as WorkflowIcon } from "lucide-react";
import Link from "next/link";

import { EmptyState, ErrorNote, LinkButton, Loading, PageHeader, StatusBadge, formatTime } from "@/components/ui";
import { useSession } from "@/lib/session";
import { useI18n } from "@/lib/i18n";
import type { Workflow } from "@/lib/types";
import { useApi } from "@/lib/useApi";

function versionState(workflow: Workflow) {
  const published = workflow.versions.find((v) => v.state === "published");
  const draft = workflow.versions.find((v) => v.state === "draft");
  if (published && draft) return `live v${published.number} · draft v${draft.number}`;
  if (published) return `live v${published.number}`;
  return `draft v${draft?.number ?? 1}`;
}

export default function WorkflowsPage() {
  const { base, can } = useSession();
  const { t } = useI18n();
  const { data, error, loading } = useApi<Workflow[]>(`${base}/workflows`);

  return (
    <>
      <PageHeader
        title={t("wf.title")}
        description={t("wf.subtitle")}
        actions={can("member") && <LinkButton href="/workflows/new">{t("dash.newWorkflow")}</LinkButton>}
      />
      <ErrorNote message={error} />
      {loading && !data ? (
        <Loading />
      ) : data && data.length === 0 ? (
        <EmptyState
          title={t("wf.empty")}
          icon={WorkflowIcon}
          action={can("member") && <LinkButton href="/workflows/new">{t("wf.create")}</LinkButton>}
        >
          {t("wf.emptyHint")}
        </EmptyState>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">{t("col.name")}</th>
                <th className="hidden px-4 py-3 font-medium sm:table-cell">{t("col.version")}</th>
                <th className="hidden px-4 py-3 font-medium md:table-cell">{t("col.updated")}</th>
                <th className="px-4 py-3 font-medium">{t("col.status")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.map((workflow) => (
                <tr key={workflow.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link href={`/workflows/${workflow.id}`} className="font-medium text-slate-900 hover:text-brand-600">
                      {workflow.name}
                    </Link>
                    {workflow.description && (
                      <p className="mt-0.5 line-clamp-1 text-xs text-slate-500">{workflow.description}</p>
                    )}
                  </td>
                  <td className="hidden px-4 py-3 text-slate-600 sm:table-cell">{versionState(workflow)}</td>
                  <td className="hidden px-4 py-3 text-slate-500 md:table-cell">{formatTime(workflow.updated_at)}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={workflow.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
