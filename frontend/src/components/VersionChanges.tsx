"use client";

import { Minus, MoveVertical, Pencil, Plus, Zap } from "lucide-react";

import { Loading } from "@/components/ui";
import { type MessageKey, useI18n } from "@/lib/i18n";
import { useSession } from "@/lib/session";
import { useApi } from "@/lib/useApi";

interface FieldChange {
  field: string;
  before: unknown;
  after: unknown;
}

interface Change {
  kind: "trigger" | "added" | "removed" | "changed";
  step_id?: string;
  name?: string;
  action?: string;
  position?: number;
  moved?: boolean;
  fields?: FieldChange[];
}

/** A value shown in one short line ("{{trigger.total}}" → "trigger.total"). */
function short(value: unknown, empty: string) {
  if (value === null || value === undefined || value === "") return empty;
  const text = typeof value === "string" ? value : JSON.stringify(value);
  const plain = text.replace(/\{\{\s*([\w.]+)\s*\}\}/g, "$1");
  return plain.length > 70 ? `${plain.slice(0, 67)}…` : plain;
}

/** Plain-language list of what differs between two workflow versions. */
export function VersionChanges({
  workflowId,
  before,
  after,
}: {
  workflowId: number;
  before?: number;
  after?: number;
}) {
  const { base } = useSession();
  const { t } = useI18n();
  const query = new URLSearchParams();
  if (before) query.set("before", String(before));
  if (after) query.set("after", String(after));
  const { data, loading } = useApi<{ changes: Change[] }>(`${base}/workflows/${workflowId}/compare?${query}`);

  if (loading && !data) return <Loading rows={1} />;
  if (!data || data.changes.length === 0) return <p className="text-sm text-slate-500">{t("diff.none")}</p>;

  const fieldLabel = (field: string) =>
    field.startsWith("inputs.")
      ? t("diff.field.input", { name: field.slice(7).replaceAll("_", " ") })
      : t(`diff.field.${field}` as MessageKey);

  return (
    <ul className="space-y-2 text-sm">
      {data.changes.map((change, index) => {
        const Icon = { trigger: Zap, added: Plus, removed: Minus, changed: Pencil }[change.kind];
        const color = {
          trigger: "text-blue-600", added: "text-emerald-600", removed: "text-red-600", changed: "text-amber-600",
        }[change.kind];
        const title =
          change.kind === "trigger" ? t("diff.trigger")
            : change.kind === "added" ? t("diff.added", { n: change.position ?? "", name: change.name ?? "" })
              : change.kind === "removed" ? t("diff.removed", { name: change.name ?? "" })
                : t("diff.changed", { name: change.name ?? "" });
        return (
          <li key={`${change.kind}-${change.step_id ?? index}`} className="flex gap-2">
            <Icon aria-hidden className={`mt-0.5 size-4 shrink-0 ${color}`} />
            <div className="min-w-0">
              <p className="font-medium text-slate-800">{title}</p>
              {(change.fields?.length || change.moved) && (
                <ul className="mt-1 space-y-0.5 text-xs text-slate-600">
                  {change.moved && (
                    <li className="flex items-center gap-1">
                      <MoveVertical aria-hidden className="size-3" /> {t("diff.moved", { n: change.position ?? "" })}
                    </li>
                  )}
                  {change.fields?.map((field) => (
                    <li key={field.field} className="break-words">
                      <span className="font-medium">{fieldLabel(field.field)}:</span>{" "}
                      <span className="text-slate-400 line-through">{short(field.before, t("diff.empty"))}</span>{" "}
                      → <span>{short(field.after, t("diff.empty"))}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
