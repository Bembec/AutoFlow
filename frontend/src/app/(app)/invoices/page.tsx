"use client";

import { FileText } from "lucide-react";
import Link from "next/link";

import { EmptyState, ErrorNote, Loading, PageHeader, formatTime } from "@/components/ui";
import { useSession } from "@/lib/session";
import { useI18n } from "@/lib/i18n";
import type { InvoiceSummary } from "@/lib/types";
import { useApi } from "@/lib/useApi";

export default function InvoicesPage() {
  const { base } = useSession();
  const { t } = useI18n();
  const { data, error, loading } = useApi<InvoiceSummary[]>(`${base}/invoices`);

  return (
    <>
      <PageHeader
        title={t("inv.title")}
        description={t("inv.subtitle")}
      />
      <ErrorNote message={error} />
      {loading && !data ? (
        <Loading />
      ) : data && data.length === 0 ? (
        <EmptyState icon={FileText} title={t("inv.empty")}>
          Install the <Link href="/workflows/new" className="text-brand-600 hover:underline">Order → invoice</Link> template
          and connect your store&apos;s &quot;order paid&quot; webhook.
        </EmptyState>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">{t("col.invoice")}</th>
                <th className="px-4 py-3 font-medium">{t("col.customer")}</th>
                <th className="hidden px-4 py-3 font-medium sm:table-cell">{t("col.order")}</th>
                <th className="hidden px-4 py-3 font-medium md:table-cell">{t("col.issued")}</th>
                <th className="px-4 py-3 text-right font-medium">{t("col.total")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.map((invoice) => (
                <tr key={invoice.number} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <a href={invoice.url} target="_blank" rel="noreferrer" className="font-medium text-brand-600 hover:underline">
                      {invoice.number}
                    </a>
                  </td>
                  <td className="px-4 py-3">
                    {invoice.customer_name}
                    <span className="block text-xs text-slate-500">{invoice.customer_email}</span>
                  </td>
                  <td className="hidden px-4 py-3 text-slate-500 sm:table-cell">{invoice.order}</td>
                  <td className="hidden px-4 py-3 text-slate-500 md:table-cell">{formatTime(invoice.issued_at)}</td>
                  <td className="px-4 py-3 text-right tabular-nums">
                    {invoice.total} {invoice.currency}
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
