"use client";

import Link from "next/link";

import { EmptyState, ErrorNote, Loading, PageHeader, formatTime } from "@/components/ui";
import { useSession } from "@/lib/session";
import type { InvoiceSummary } from "@/lib/types";
import { useApi } from "@/lib/useApi";

export default function InvoicesPage() {
  const { base } = useSession();
  const { data, error, loading } = useApi<InvoiceSummary[]>(`${base}/invoices`);

  return (
    <>
      <PageHeader
        title="Invoices"
        description="Created by your order workflows: one per order, numbered in sequence. Business details come from Settings."
      />
      <ErrorNote message={error} />
      {loading && !data ? (
        <Loading />
      ) : data && data.length === 0 ? (
        <EmptyState title="No invoices yet">
          Install the <Link href="/workflows/new" className="text-indigo-600 hover:underline">Order → invoice</Link> template
          and connect your store&apos;s &quot;order paid&quot; webhook.
        </EmptyState>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">Invoice</th>
                <th className="px-4 py-3 font-medium">Customer</th>
                <th className="hidden px-4 py-3 font-medium sm:table-cell">Order</th>
                <th className="hidden px-4 py-3 font-medium md:table-cell">Issued</th>
                <th className="px-4 py-3 text-right font-medium">Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.map((invoice) => (
                <tr key={invoice.number} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <a href={invoice.url} target="_blank" rel="noreferrer" className="font-medium text-indigo-600 hover:underline">
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
