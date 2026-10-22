"use client";

import Link from "next/link";

import { EmptyState, ErrorNote, LinkButton, Loading, PageHeader, StatusBadge, formatTime } from "@/components/ui";
import { useSession } from "@/lib/session";
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
  const { data, error, loading } = useApi<Workflow[]>(`${base}/workflows`);

  return (
    <>
      <PageHeader
        title="Workflows"
        description="Each workflow is a trigger plus steps. Test with sample data, then publish to run it for real."
        actions={can("member") && <LinkButton href="/workflows/new">New workflow</LinkButton>}
      />
      <ErrorNote message={error} />
      {loading && !data ? (
        <Loading />
      ) : data && data.length === 0 ? (
        <EmptyState title="No workflows yet">
          Describe a task in plain words and AutoFlow drafts it for you.{" "}
          <Link href="/workflows/new" className="text-indigo-600 hover:underline">Create one</Link>
        </EmptyState>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="hidden px-4 py-3 font-medium sm:table-cell">Version</th>
                <th className="hidden px-4 py-3 font-medium md:table-cell">Updated</th>
                <th className="px-4 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.map((workflow) => (
                <tr key={workflow.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link href={`/workflows/${workflow.id}`} className="font-medium text-slate-900 hover:text-indigo-600">
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
