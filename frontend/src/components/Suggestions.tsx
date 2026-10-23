"use client";

import { AlertTriangle, Lightbulb, Settings2, type LucideIcon } from "lucide-react";
import { useRouter } from "next/navigation";

import { Button, ErrorNote, LinkButton } from "@/components/ui";
import { api } from "@/lib/api";
import { type MessageKey, useI18n } from "@/lib/i18n";
import { useSession } from "@/lib/session";
import type { Suggestion, Workflow } from "@/lib/types";
import { useAction } from "@/lib/useApi";

const KINDS: Record<Suggestion["kind"], { icon: LucideIcon; className: string }> = {
  fix: { icon: AlertTriangle, className: "bg-orange-50 text-orange-600" },
  setup: { icon: Settings2, className: "bg-blue-50 text-blue-600" },
  automate: { icon: Lightbulb, className: "bg-brand-50 text-brand-600" },
};

/** "What to do next" cards: fixes, setup gaps and automations worth adding. */
export function SuggestionList({ suggestions }: { suggestions: Suggestion[] }) {
  const { base, can } = useSession();
  const { t } = useI18n();
  const router = useRouter();
  const install = useAction();

  // Text in the user's language, falling back to the server's English
  function text(item: Suggestion, part: "title" | "reason") {
    const key = `sug.${item.key}.${part}` as MessageKey;
    const translated = t(key, item.vars);
    return translated === key ? item[part] : translated;
  }

  async function use(template: string) {
    const workflow = await install.run(() => api<Workflow>(`${base}/workflows/from-template`, { body: { template } }));
    if (workflow) router.push(`/workflows/${workflow.id}?tab=run`);
  }

  if (suggestions.length === 0) return <p className="text-sm text-slate-500">{t("ins.nothing")}</p>;

  return (
    <>
      <ErrorNote message={install.error} />
      <ul className="space-y-3">
        {suggestions.map((item) => {
          const { icon: Icon, className } = KINDS[item.kind];
          return (
            <li key={item.id} className="flex flex-wrap items-start gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:flex-nowrap">
              <span className={`flex size-9 shrink-0 items-center justify-center rounded-lg ${className}`}>
                <Icon aria-hidden className="size-5" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium text-slate-500">{t(`ins.kind.${item.kind}` as MessageKey)}</p>
                <p className="font-medium text-slate-900">{text(item, "title")}</p>
                <p className="mt-1 text-sm text-slate-600">{text(item, "reason")}</p>
              </div>
              <div className="shrink-0">
                {item.template && can("member") ? (
                  <Button variant="secondary" disabled={install.busy} onClick={() => use(item.template!)}>
                    {t("gs.install")}
                  </Button>
                ) : item.link ? (
                  <LinkButton href={item.link} variant="secondary">{t("ins.open")}</LinkButton>
                ) : null}
              </div>
            </li>
          );
        })}
      </ul>
    </>
  );
}
