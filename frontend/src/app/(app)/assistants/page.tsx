"use client";

import { Bot, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button, Card, EmptyState, ErrorNote, LinkButton, Loading, PageHeader, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { useSession } from "@/lib/session";
import type { Workflow } from "@/lib/types";
import { useAction, useApi } from "@/lib/useApi";

interface Role {
  slug: string;
  name: string;
  description: string;
  requires: string[];
  looks_up: string[];
  proposes: string[];
}

interface ActiveAssistant {
  workflow_id: number;
  name: string;
  role: string;
  status: string;
  live: boolean;
  handled_7d: number;
  succeeded_7d: number;
  failed_7d: number;
  waiting_approval: number;
}

// Plain names for the tools and actions a role uses
const LABELS: Record<string, string> = {
  checkout_status: "checkout status",
  exchange_rate_quote: "exchange rates",
  http_get: "your shop's API",
  mcp_read: "read-only MCP tools",
  shopify_tag_order: "tag Shopify orders",
  shopify_set_order_note: "add Shopify order notes",
  void_invoice: "void invoices",
  airtable_upsert: "update Airtable records",
  record_order: "record orders",
  save_customer: "save customers",
  log_activity: "write to the activity log",
};

const label = (name: string) => LABELS[name] ?? name.replaceAll("_", " ");

export default function AssistantsPage() {
  const { base, can } = useSession();
  const { t } = useI18n();
  const router = useRouter();
  const { data, error, loading, reload } = useApi<{ roles: Role[]; active: ActiveAssistant[] }>(`${base}/assistants`);
  const action = useAction();
  const [installing, setInstalling] = useState<string | null>(null);

  if (loading && !data) return <Loading />;
  if (!data) return <ErrorNote message={error} />;

  async function setUp(slug: string) {
    setInstalling(slug);
    const workflow = await action.run(() => api<Workflow>(`${base}/workflows/from-template`, { body: { template: slug } }));
    setInstalling(null);
    if (workflow) router.push(`/workflows/${workflow.id}?tab=run`);
  }

  async function toggle(assistant: ActiveAssistant) {
    const verb = assistant.status === "active" ? "pause" : "resume";
    await action.run(() => api(`${base}/workflows/${assistant.workflow_id}/${verb}`, { body: {} }));
    reload();
  }

  return (
    <>
      <PageHeader title={t("nav.assistants")} description={t("as.subtitle")} />
      <p className="mb-6 flex items-center gap-2 text-sm text-emerald-800">
        <ShieldCheck aria-hidden className="size-4" />
        {t("as.approvalNote")}
      </p>
      <ErrorNote message={action.error} />

      <h2 className="mb-3 font-semibold">{t("as.active")}</h2>
      {data.active.length === 0 ? (
        <EmptyState icon={Bot} title={t("as.none")} />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {data.active.map((assistant) => (
            <Card key={assistant.workflow_id}>
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-semibold">{assistant.name}</h3>
                <StatusBadge status={assistant.live ? assistant.status : "draft"} />
              </div>
              <ul className="mt-3 space-y-1 text-sm text-slate-600">
                {!assistant.live && <li className="text-amber-800">{t("as.notLive")}</li>}
                <li>{t("as.handled", { n: assistant.handled_7d })}</li>
                {assistant.waiting_approval > 0 && (
                  <li>
                    <Link href="/approvals" className="font-medium text-amber-800 hover:underline">
                      {t("as.waiting", { n: assistant.waiting_approval })}
                    </Link>
                  </li>
                )}
                {assistant.failed_7d > 0 && <li className="text-orange-700">{t("as.failed", { n: assistant.failed_7d })}</li>}
              </ul>
              <div className="mt-4 flex flex-wrap gap-2">
                <LinkButton href={`/workflows/${assistant.workflow_id}`} variant="secondary">{t("as.open")}</LinkButton>
                {can("member") && assistant.live && (
                  <Button variant="ghost" disabled={action.busy} onClick={() => toggle(assistant)}>
                    {assistant.status === "active" ? t("wfd.pause") : t("wfd.resume")}
                  </Button>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      <h2 className="mt-10 mb-3 font-semibold">{t("as.roles")}</h2>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {data.roles.map((role) => (
          <Card key={role.slug} className="flex flex-col">
            <span className="mb-3 flex size-10 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
              <Bot aria-hidden className="size-5" />
            </span>
            <h3 className="font-semibold">{role.name}</h3>
            <p className="mt-1 flex-1 text-sm text-slate-600">{role.description}</p>
            <dl className="mt-4 space-y-1 text-xs">
              <div>
                <dt className="inline font-medium text-slate-700">{t("as.looksUp")}: </dt>
                <dd className="inline text-slate-600">{role.looks_up.map(label).join(", ") || t("as.nothing")}</dd>
              </div>
              <div>
                <dt className="inline font-medium text-slate-700">{t("as.proposes")}: </dt>
                <dd className="inline text-slate-600">{role.proposes.map(label).join(", ") || t("as.nothing")}</dd>
              </div>
            </dl>
            <details className="mt-3 text-xs text-slate-600">
              <summary className="cursor-pointer font-medium text-slate-700">{t("as.needs")}</summary>
              <ul className="mt-1 list-disc space-y-0.5 pl-4">
                {role.requires.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </details>
            {can("member") && (
              <Button className="mt-4" disabled={action.busy} onClick={() => setUp(role.slug)}>
                {installing === role.slug ? t("as.settingUp") : t("as.setUp")}
              </Button>
            )}
          </Card>
        ))}
      </div>
    </>
  );
}
