"use client";

import { FileText } from "lucide-react";
import Link from "next/link";

import { Button, EmptyState, ErrorNote, Loading, PageHeader, formatTime } from "@/components/ui";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";
import { useI18n } from "@/lib/i18n";
import type { InvoiceSummary } from "@/lib/types";
import { useAction, useApi } from "@/lib/useApi";

export default function InvoicesPage() {
  const { base, can } = useSession();
  const { t } = useI18n();
  const { data, error, loading, reload } = useApi<InvoiceSummary[]>(`${base}/invoices`);
  const action = useAction();

  async function voidInvoice(invoice: InvoiceSummary) {
    const reason = window.prompt(t("inv.voidAsk"), "");
    if (!reason || reason.trim().length < 3) return;
    await action.run(() => api(`${base}/invoices/${invoice.id}/void`, { body: { reason: reason.trim() } }));
    reload();
  }

  return (
    <>
      <PageHeader
        title={t("inv.title")}
        description={t("inv.subtitle")}
      />
      <ErrorNote message={error ?? action.error} />
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
                <th className="px-4 py-3 font-medium"><span className="sr-only">{t("col.status")}</span></th>
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
                  <td className={`px-4 py-3 text-right tabular-nums ${invoice.voided_at ? "text-slate-400 line-through" : ""}`}>
                    {invoice.total} {invoice.currency}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {invoice.voided_at ? (
                      <span
                        title={invoice.void_reason ?? undefined}
                        className="inline-flex rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700 ring-1 ring-inset ring-red-600/20"
                      >
                        {t("inv.voided")}
                      </span>
                    ) : can("member") ? (
                      <Button variant="ghost" className="px-2 py-1 text-xs" disabled={action.busy} onClick={() => voidInvoice(invoice)}>
                        {t("inv.void")}
                      </Button>
                    ) : null}
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
