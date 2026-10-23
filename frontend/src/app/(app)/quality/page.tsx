"use client";

import { CheckCircle2, Gauge } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Button, Card, EmptyState, ErrorNote, Field, JsonBlock, Loading, PageHeader, Tabs, formatTime, inputClass } from "@/components/ui";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { useSession } from "@/lib/session";
import { useAction, useApi } from "@/lib/useApi";

interface Overview {
  sample_percent: number;
  sampled: number;
  waiting: number;
  reviewed: number;
  good_rate: number | null;
  per_action: { action: string; sampled: number; reviewed: number; good: number; good_rate: number | null }[];
  weekly_good_rate: (number | null)[];
}

interface Sample {
  id: number;
  execution_id: number;
  workflow: string | null;
  step_id: string;
  action: string;
  input: unknown;
  output: Record<string, unknown> | null;
  confidence: number | null;
  verdict: "good" | "bad" | null;
  note: string | null;
  created_at: string;
}

const percent = (rate: number | null) => (rate === null ? "—" : `${Math.round(rate * 100)}%`);
const actionName = (name: string) => name.replace(/^ai_/, "").replaceAll("_", " ");

export default function QualityPage() {
  const { base, can } = useSession();
  const { t } = useI18n();
  const [view, setView] = useState<"waiting" | "reviewed">("waiting");
  const overview = useApi<Overview>(`${base}/quality`);
  const samples = useApi<Sample[]>(`${base}/quality/samples?status=${view}`);

  if (overview.loading && !overview.data) return <Loading />;
  if (!overview.data) return <ErrorNote message={overview.error} />;
  const data = overview.data;

  return (
    <>
      <PageHeader title={t("q.title")} description={t("q.subtitle")} />

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <p className="text-sm text-slate-500">{t("q.goodRate")}</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">{percent(data.good_rate)}</p>
        </Card>
        <Card>
          <p className="text-sm text-slate-500">{t("q.waiting")}</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">{data.waiting}</p>
        </Card>
        <Card>
          <p className="text-sm text-slate-500">{t("q.reviewed")}</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">{data.reviewed}</p>
        </Card>
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-3">
        <div className="space-y-4 xl:col-span-2">
          <Tabs
            tabs={[{ id: "waiting", label: t("q.waiting") }, { id: "reviewed", label: t("q.reviewed") }]}
            value={view}
            onChange={setView}
            label={t("q.title")}
          />
          {samples.loading && !samples.data ? (
            <Loading rows={2} />
          ) : samples.data && samples.data.length === 0 ? (
            <EmptyState icon={CheckCircle2} title={t("q.empty")} />
          ) : (
            samples.data?.map((sample) => (
              <SampleCard
                key={sample.id}
                sample={sample}
                canJudge={can("member") && !sample.verdict}
                onJudged={() => {
                  samples.reload();
                  overview.reload();
                }}
              />
            ))
          )}
        </div>

        <div className="space-y-6">
          <Card>
            <h2 className="font-semibold">{t("q.byStep")}</h2>
            {data.per_action.length === 0 ? (
              <p className="mt-2 text-sm text-slate-500">—</p>
            ) : (
              <ul className="mt-3 space-y-2 text-sm">
                {data.per_action.map((row) => (
                  <li key={row.action} className="flex justify-between gap-2">
                    <span className="capitalize">{actionName(row.action)}</span>
                    <span className="tabular-nums text-slate-600">
                      {percent(row.good_rate)} · {row.reviewed}/{row.sampled}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <SamplingCard current={data.sample_percent} onSaved={overview.reload} />
        </div>
      </div>
    </>
  );
}

function SampleCard({ sample, canJudge, onJudged }: { sample: Sample; canJudge: boolean; onJudged: () => void }) {
  const { base } = useSession();
  const { t } = useI18n();
  const action = useAction();
  const [note, setNote] = useState("");

  async function judge(verdict: "good" | "bad") {
    const done = await action.run(() =>
      api(`${base}/quality/samples/${sample.id}`, { body: { verdict, note: note.trim() || null } }),
    );
    if (done !== undefined) onJudged();
  }

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-medium capitalize">{actionName(sample.action)}</p>
          <p className="text-xs text-slate-500">
            {sample.workflow} ·{" "}
            <Link href={`/executions/${sample.execution_id}`} className="hover:text-brand-600">#{sample.execution_id}</Link>
            {" · "}{formatTime(sample.created_at)}
            {sample.confidence !== null && <> · {Math.round(sample.confidence * 100)}%</>}
          </p>
        </div>
        {sample.verdict && (
          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${sample.verdict === "good" ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"}`}>
            {sample.verdict === "good" ? t("q.good") : t("q.bad")}
          </span>
        )}
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <div>
          <p className="mb-1 text-xs font-medium uppercase text-slate-500">{t("q.went_in")}</p>
          <JsonBlock value={sample.input} />
        </div>
        <div>
          <p className="mb-1 text-xs font-medium uppercase text-slate-500">{t("q.came_out")}</p>
          <JsonBlock value={sample.output} />
        </div>
      </div>
      {sample.note && <p className="mt-2 text-sm text-slate-700">“{sample.note}”</p>}
      {canJudge && (
        <div className="mt-3 space-y-2">
          <input className={inputClass} placeholder={t("q.note")} value={note} maxLength={1000}
                 onChange={(e) => setNote(e.target.value)} aria-label={t("q.note")} />
          <div className="flex gap-2">
            <Button disabled={action.busy} onClick={() => judge("good")}>{t("q.good")}</Button>
            <Button variant="secondary" disabled={action.busy} onClick={() => judge("bad")}>{t("q.bad")}</Button>
          </div>
          <ErrorNote message={action.error} />
        </div>
      )}
    </Card>
  );
}

function SamplingCard({ current, onSaved }: { current: number; onSaved: () => void }) {
  const { base, can } = useSession();
  const { t } = useI18n();
  const action = useAction();
  const [value, setValue] = useState(String(current));
  if (!can("admin")) return null;

  return (
    <Card>
      <form
        className="space-y-3"
        onSubmit={async (event) => {
          event.preventDefault();
          const saved = await action.run(() =>
            api(`${base}/quality/settings`, { method: "PUT", body: { sample_percent: Number(value) } }),
          );
          if (saved !== undefined) onSaved();
        }}
      >
        <Field label={t("q.rate")} hint={t("q.rateHint")}>
          <div className="flex items-center gap-2">
            <input className={`${inputClass} w-24`} type="number" min={0} max={20} value={value}
                   onChange={(e) => setValue(e.target.value)} />
            <span className="text-sm text-slate-500">%</span>
          </div>
        </Field>
        <ErrorNote message={action.error} />
        <Button type="submit" variant="secondary" disabled={action.busy}>
          <Gauge aria-hidden className="size-4" />
          {t("common.save")}
        </Button>
      </form>
    </Card>
  );
}
