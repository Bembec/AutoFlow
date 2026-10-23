"use client";

import { ShoppingBag, Sparkles, Store, Wand2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { OnboardingChecklist } from "@/components/OnboardingChecklist";
import { Button, Card, ErrorNote, LinkButton, Loading, PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { useSession } from "@/lib/session";
import type { TemplateInfo, Workflow } from "@/lib/types";
import { useAction, useApi } from "@/lib/useApi";

type Platform = "shopify" | "woocommerce" | "other";

// Best first automation per platform, then the useful follow-ups
const PICKS: Record<Platform, string[]> = {
  shopify: ["shopify-order-to-invoice", "abandoned-cart-follow-up", "shipping-notification"],
  woocommerce: ["woocommerce-order-to-invoice", "woocommerce-packing-note", "refund-void-invoice"],
  other: ["shopify-order-to-invoice", "support-inbox-assistant", "supplier-invoice-to-sheet"],
};

export default function GetStartedPage() {
  const { base, can } = useSession();
  const { t } = useI18n();
  const router = useRouter();
  const { data: templates, error, loading } = useApi<TemplateInfo[]>("/templates");
  const { data: workflows } = useApi<Workflow[]>(`${base}/workflows`);
  const install = useAction();
  const [platform, setPlatform] = useState<Platform>("shopify");
  const [installing, setInstalling] = useState<string | null>(null);

  const platforms: { id: Platform; label: string; icon: typeof Store }[] = [
    { id: "shopify", label: "Shopify", icon: ShoppingBag },
    { id: "woocommerce", label: "WooCommerce", icon: Store },
    { id: "other", label: t("gs.other"), icon: Sparkles },
  ];

  const bySlug = new Map(templates?.map((template) => [template.slug, template]));
  const [recommended, ...also] = PICKS[platform].map((slug) => bySlug.get(slug)).filter((item) => item !== undefined);

  async function use(slug: string) {
    setInstalling(slug);
    const workflow = await install.run(() =>
      api<Workflow>(`${base}/workflows/from-template`, { body: { template: slug } }),
    );
    setInstalling(null);
    // Straight to the Run tab: the next checklist step is a test with sample data
    if (workflow) router.push(`/workflows/${workflow.id}?tab=run`);
  }

  return (
    <>
      <PageHeader title={t("gs.title")} description={t("gs.subtitle")} />
      <ErrorNote message={error ?? install.error} />

      <fieldset className="mb-6">
        <legend className="mb-2 text-sm font-medium text-slate-700">{t("gs.where")}</legend>
        <div className="grid gap-3 sm:grid-cols-3">
          {platforms.map(({ id, label, icon: Icon }) => {
            const selected = platform === id;
            return (
              <label
                key={id}
                className={`flex cursor-pointer items-center gap-3 rounded-xl border bg-white p-4 transition-colors has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-brand-500 ${
                  selected ? "border-brand-500 ring-1 ring-brand-500" : "border-slate-200 hover:border-slate-300"
                }`}
              >
                <input
                  type="radio"
                  name="platform"
                  value={id}
                  checked={selected}
                  onChange={() => setPlatform(id)}
                  className="sr-only"
                />
                <span
                  className={`flex size-10 items-center justify-center rounded-lg ${
                    selected ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-500"
                  }`}
                >
                  <Icon aria-hidden className="size-5" />
                </span>
                <span className="font-medium">{label}</span>
              </label>
            );
          })}
        </div>
      </fieldset>

      {loading && !templates ? (
        <Loading rows={2} />
      ) : (
        recommended && (
          <div className="grid gap-6 lg:grid-cols-3">
            <Card className="border-brand-200 lg:col-span-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">{t("gs.recommended")}</p>
              <h2 className="mt-1 text-xl font-semibold">{recommended.name}</h2>
              <p className="mt-2 text-sm text-slate-600">{recommended.description}</p>
              {recommended.requires.length > 0 && (
                <>
                  <p className="mt-4 text-sm font-medium text-slate-700">{t("gs.needs")}</p>
                  <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-slate-600">
                    {recommended.requires.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </>
              )}
              {can("member") && (
                <Button className="mt-5" disabled={install.busy} onClick={() => use(recommended.slug)}>
                  {installing === recommended.slug ? t("gs.installing") : t("gs.install")}
                </Button>
              )}
            </Card>

            <div className="space-y-3">
              <p className="text-sm font-medium text-slate-700">{t("gs.also")}</p>
              {also.map((template) => (
                <Card key={template.slug} className="p-4">
                  <h3 className="font-medium">{template.name}</h3>
                  <p className="mt-1 line-clamp-3 text-xs text-slate-500">{template.description}</p>
                  {can("member") && (
                    <Button
                      variant="secondary"
                      className="mt-3"
                      disabled={install.busy}
                      onClick={() => use(template.slug)}
                    >
                      {installing === template.slug ? t("gs.installing") : t("gs.install")}
                    </Button>
                  )}
                </Card>
              ))}
            </div>
          </div>
        )
      )}

      <Card className="mt-6 flex flex-wrap items-center justify-between gap-3">
        <p className="flex items-center gap-2 text-sm text-slate-600">
          <Wand2 aria-hidden className="size-4 text-brand-600" />
          {t("gs.custom")}
        </p>
        <LinkButton href="/workflows/new" variant="secondary">{t("gs.describe")}</LinkButton>
      </Card>

      <div className="mt-8">
        <OnboardingChecklist workflowId={workflows?.[0]?.id} />
      </div>
      <p className="text-center text-sm">
        <Link href="/dashboard" className="text-slate-500 hover:text-slate-900">{t("gs.skip")}</Link>
      </p>
    </>
  );
}
