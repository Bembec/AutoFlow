"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { WorkflowCanvas } from "@/components/WorkflowCanvas";
import { Button, Card, ErrorNote, PageHeader, inputClass } from "@/components/ui";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";
import { useI18n } from "@/lib/i18n";
import type { AIDraft, TemplateInfo, Workflow } from "@/lib/types";
import { useAction, useApi } from "@/lib/useApi";

const EXAMPLES = [
  "When a customer sends an enquiry, classify it. For sales questions quote our 100 EUR package in USD, save the customer and email them a reply after I approve it.",
  "When an invoice email arrives, extract the invoice number, supplier, total and due date, and add them as a row in our Google Sheet.",
  "When a support message comes in, check if the customer sounds angry. If so, draft a calm reply for me to approve.",
];

export default function NewWorkflowPage() {
  const router = useRouter();
  const { base, can } = useSession();
  const { t } = useI18n();
  const { data: templates } = useApi<TemplateInfo[]>("/templates");
  const draftAction = useAction();
  const saveAction = useAction();

  const [request, setRequest] = useState("");
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [draft, setDraft] = useState<AIDraft | null>(null);

  async function askAI(event?: React.FormEvent) {
    event?.preventDefault();
    const answered = Object.entries(answers)
      .filter(([, answer]) => answer.trim())
      .map(([question, answer]) => ({ question, answer }));

    const result = await draftAction.run(() =>
      api<AIDraft>(`${base}/workflows/ai-draft`, { body: { request, answers: answered } }),
    );
    if (result) setDraft(result);
  }

  async function saveDraft() {
    if (!draft?.definition) return;
    const workflow = await saveAction.run(() =>
      api<Workflow>(`${base}/workflows`, {
        body: { name: draft.name, description: draft.description, definition: draft.definition },
      }),
    );
    if (workflow) router.push(`/workflows/${workflow.id}`);
  }

  async function installTemplate(slug: string) {
    const workflow = await saveAction.run(() =>
      api<Workflow>(`${base}/workflows/from-template`, { body: { template: slug } }),
    );
    if (workflow) router.push(`/workflows/${workflow.id}`);
  }

  if (!can("member")) {
    return <ErrorNote message="You need the member role or higher to create workflows." />;
  }

  return (
    <>
      <PageHeader
        title={t("new.title")}
        description={t("new.subtitle")}
      />

      <div className="grid gap-6 xl:grid-cols-5">
        <div className="space-y-6 xl:col-span-2">
          <Card>
            <form onSubmit={askAI} className="space-y-3">
              <label htmlFor="request" className="font-semibold">{t("new.ask")}</label>
              <textarea
                id="request"
                className={`${inputClass} min-h-32`}
                placeholder="When … then …"
                value={request}
                onChange={(event) => setRequest(event.target.value)}
                minLength={10}
                required
              />
              <div className="flex flex-wrap gap-2">
                {EXAMPLES.map((example) => (
                  <button
                    key={example}
                    type="button"
                    onClick={() => setRequest(example)}
                    className="rounded-full border border-slate-200 px-3 py-1 text-left text-xs text-slate-600 hover:border-brand-300 hover:text-brand-700"
                  >
                    {example.slice(0, 48)}…
                  </button>
                ))}
              </div>

              {draft?.questions.length ? (
                <div className="space-y-3 rounded-lg bg-amber-50 p-3">
                  <p className="text-sm font-medium text-amber-900">{t("new.details")}</p>
                  {draft.questions.map((question) => (
                    <label key={question} className="block text-sm">
                      <span className="text-amber-900">{question}</span>
                      <input
                        className={`${inputClass} mt-1`}
                        value={answers[question] ?? ""}
                        onChange={(event) => setAnswers({ ...answers, [question]: event.target.value })}
                      />
                    </label>
                  ))}
                </div>
              ) : null}

              <ErrorNote message={draftAction.error} />
              <Button type="submit" disabled={draftAction.busy || request.trim().length < 10}>
                {draftAction.busy ? t("new.drafting") : draft ? t("new.update") : t("new.draft")}
              </Button>
            </form>
          </Card>

          <Card>
            <h2 className="font-semibold">{t("new.templates")}</h2>
            <ul className="mt-3 space-y-3">
              {templates?.map((template) => (
                <li key={template.slug} className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium">
                      {template.name}
                      <span className="ml-2 rounded-full bg-brand-50 px-2 py-0.5 text-[11px] font-normal text-brand-700">
                        {template.category}
                      </span>
                    </p>
                    <p className="text-xs text-slate-500">{template.description}</p>
                    {template.requires.length > 0 && (
                      <details className="mt-1 text-xs text-slate-500">
                        <summary className="cursor-pointer">{t("new.needs")}</summary>
                        <ul className="mt-1 list-disc space-y-0.5 pl-4">
                          {template.requires.map((item) => <li key={item}>{item}</li>)}
                        </ul>
                      </details>
                    )}
                  </div>
                  <Button variant="secondary" disabled={saveAction.busy} onClick={() => installTemplate(template.slug)}>
                    {t("new.use")}
                  </Button>
                </li>
              ))}
            </ul>
          </Card>
        </div>

        <div className="xl:col-span-3">
          {draft?.definition ? (
            <Card>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="font-semibold">{draft.name}</h2>
                  <p className="text-sm text-slate-500">{draft.description}</p>
                </div>
                <Button onClick={saveDraft} disabled={saveAction.busy}>
                  {saveAction.busy ? t("new.saving") : t("new.save")}
                </Button>
              </div>
              <div className="mt-4">
                <WorkflowCanvas definition={draft.definition} />
              </div>
              {draft.assumptions.length > 0 && (
                <div className="mt-4 text-sm">
                  <p className="font-medium">{t("new.assumptions")}</p>
                  <ul className="mt-1 list-disc space-y-1 pl-5 text-slate-600">
                    {draft.assumptions.map((item) => <li key={item}>{item}</li>)}
                  </ul>
                </div>
              )}
              {draft.unsupported.length > 0 && (
                <p className="mt-3 rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-600">
                  {t("new.unsupported")} {draft.unsupported.join(", ")}
                </p>
              )}
              <ErrorNote message={saveAction.error} />
            </Card>
          ) : (
            <div className="flex h-full min-h-64 items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
              {t("new.placeholder")}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
