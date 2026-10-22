"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { StepEditor } from "@/components/StepEditor";
import { WorkflowCanvas } from "@/components/WorkflowCanvas";
import { Button, Card, ErrorNote, Field, JsonBlock, Loading, StatusBadge, formatTime, inputClass } from "@/components/ui";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";
import type { ActionInfo, Definition, Execution, Workflow } from "@/lib/types";
import { useAction, useApi } from "@/lib/useApi";

type Tab = "run" | "edit" | "versions" | "trigger" | "settings";

function parseJson(text: string): { value?: unknown; error?: string } {
  try {
    return { value: JSON.parse(text) };
  } catch (error) {
    return { error: `Invalid JSON: ${(error as Error).message}` };
  }
}

export default function WorkflowPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { base, can } = useSession();
  const { data: workflow, error, loading, reload, setData } = useApi<Workflow>(`${base}/workflows/${id}`);
  const { data: actions } = useApi<ActionInfo[]>("/actions");
  const action = useAction();
  const [tab, setTab] = useState<Tab>("run");
  const [selectedStep, setSelectedStep] = useState<string | null>(null);
  const [lastRun, setLastRun] = useState<Execution | null>(null);

  const draft = workflow?.versions.find((v) => v.state === "draft");
  const published = workflow?.versions.find((v) => v.state === "published");
  const current = draft ?? published;
  const definition = current?.definition;

  const stepStatus = useMemo(
    () => (lastRun ? Object.fromEntries(lastRun.steps.map((s) => [s.step_id, s.status])) : undefined),
    [lastRun],
  );

  if (loading && !workflow) return <Loading />;
  if (error) return <ErrorNote message={error} />;
  if (!workflow || !definition) return null;

  const editable = can("member") && workflow.status !== "archived";
  const step = definition.steps.find((s) => s.id === selectedStep);
  const stepAction = actions?.find((a) => a.name === step?.action);
  const stepRun = lastRun?.steps.find((s) => s.step_id === selectedStep);

  async function saveDefinition(next: Definition) {
    const updated = await action.run(() =>
      api<Workflow>(`${base}/workflows/${id}`, { method: "PATCH", body: { definition: next } }),
    );
    if (updated) setData(updated);
    return Boolean(updated);
  }

  async function workflowAction(path: string, body?: unknown) {
    const updated = await action.run(() => api<Workflow>(`${base}/workflows/${id}/${path}`, { body: body ?? {} }));
    if (updated) setData(updated);
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: "run", label: "Run" },
    { id: "edit", label: "Edit" },
    { id: "trigger", label: "Trigger" },
    { id: "versions", label: "Versions" },
    { id: "settings", label: "Settings" },
  ];

  return (
    <>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <Link href="/workflows" className="text-sm text-slate-500 hover:text-slate-800">← Workflows</Link>
          <h1 className="mt-1 text-2xl font-semibold">{workflow.name}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-slate-500">
            <StatusBadge status={workflow.status} />
            {published && <span>Live: v{published.number}</span>}
            {draft && <span>Draft: v{draft.number} (not live yet)</span>}
          </div>
        </div>
        {editable && (
          <div className="flex flex-wrap gap-2">
            {draft && (
              <Button onClick={() => workflowAction("publish")} disabled={action.busy}>
                Publish v{draft.number}
              </Button>
            )}
            {workflow.status === "active" ? (
              <Button variant="secondary" onClick={() => workflowAction("pause")} disabled={action.busy}>
                Pause
              </Button>
            ) : workflow.status === "paused" ? (
              <Button variant="secondary" onClick={() => workflowAction("resume")} disabled={action.busy}>
                Resume
              </Button>
            ) : null}
            <Button
              variant="ghost"
              disabled={action.busy}
              onClick={async () => {
                if (!window.confirm("Archive this workflow? It will stop running and be hidden.")) return;
                await workflowAction("archive");
                router.push("/workflows");
              }}
            >
              Archive
            </Button>
          </div>
        )}
      </div>

      <ErrorNote message={action.error} />

      <div className="mt-4 grid gap-6 xl:grid-cols-5">
        <div className="space-y-4 xl:col-span-3">
          <WorkflowCanvas
            definition={definition}
            stepStatus={stepStatus}
            selectedStep={selectedStep}
            onSelectStep={setSelectedStep}
          />
          {step ? (
            <Card>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h2 className="font-semibold">{step.name ?? step.id}</h2>
                  <p className="text-sm text-slate-500">{stepAction?.description ?? step.action}</p>
                </div>
                <code className="rounded bg-slate-100 px-2 py-0.5 text-xs">{step.action}</code>
              </div>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <div>
                  <p className="mb-1 text-xs font-medium uppercase text-slate-500">Step settings</p>
                  <JsonBlock value={{ inputs: step.inputs, when: step.when, retry: step.retry, timeout_seconds: step.timeout_seconds }} />
                </div>
                {stepRun && (
                  <div>
                    <p className="mb-1 text-xs font-medium uppercase text-slate-500">
                      Last run · {stepRun.status} · {stepRun.attempts} attempt(s)
                    </p>
                    <JsonBlock value={stepRun.error ? { error: stepRun.error } : stepRun.output} />
                  </div>
                )}
              </div>
            </Card>
          ) : (
            <p className="text-sm text-slate-500">Click a step to see its settings and last result.</p>
          )}
        </div>

        <div className="xl:col-span-2">
          <div className="mb-3 flex flex-wrap gap-1 rounded-lg bg-slate-100 p-1">
            {tabs.map((item) => (
              <button
                key={item.id}
                onClick={() => setTab(item.id)}
                className={`rounded-md px-3 py-1.5 text-sm ${tab === item.id ? "bg-white font-medium shadow-sm" : "text-slate-600"}`}
              >
                {item.label}
              </button>
            ))}
          </div>

          {tab === "run" && (
            <RunPanel
              key={`${current.number}-${workflow.updated_at}`}
              workflow={workflow}
              definition={definition}
              canRun={can("member")}
              onRun={setLastRun}
            />
          )}
          {tab === "edit" && (
            <>
              <StepEditor
                key={`${current.number}-${workflow.updated_at}`}
                definition={definition}
                actions={actions ?? []}
                editable={editable}
                selectedStep={selectedStep}
                onSelectStep={setSelectedStep}
                onSave={saveDefinition}
                error={action.error}
              />
              <details className="mt-4">
                <summary className="cursor-pointer text-sm text-slate-600">Advanced: edit as JSON</summary>
                <div className="mt-2">
                  <EditPanel
                    key={`json-${current.number}-${workflow.updated_at}`}
                    definition={definition}
                    editable={editable}
                    actions={actions ?? []}
                    onSave={saveDefinition}
                    error={action.error}
                  />
                </div>
              </details>
            </>
          )}
          {tab === "trigger" && <TriggerPanel workflow={workflow} definition={definition} editable={editable} />}
          {tab === "versions" && (
            <Card>
              <ul className="divide-y divide-slate-100">
                {[...workflow.versions].reverse().map((version) => (
                  <li key={version.number} className="flex items-center justify-between gap-2 py-2.5 text-sm">
                    <span>
                      v{version.number} <StatusBadge status={version.state} />
                      <span className="ml-2 text-xs text-slate-500">
                        {formatTime(version.published_at ?? version.created_at)}
                      </span>
                    </span>
                    {editable && version.state === "archived" && (
                      <Button variant="secondary" onClick={() => workflowAction("publish", { version: version.number })}>
                        Roll back to this
                      </Button>
                    )}
                  </li>
                ))}
              </ul>
            </Card>
          )}
          {tab === "settings" && (
            <SettingsPanel
              workflow={workflow}
              editable={editable}
              onSaved={(updated) => setData(updated)}
            />
          )}
          {action.busy && <p className="mt-2 text-xs text-slate-500">Working…</p>}
          <button onClick={reload} className="mt-3 text-xs text-slate-500 hover:text-slate-800">Refresh</button>
        </div>
      </div>
    </>
  );
}

function RunPanel({
  workflow,
  definition,
  canRun,
  onRun,
}: {
  workflow: Workflow;
  definition: Definition;
  canRun: boolean;
  onRun: (execution: Execution) => void;
}) {
  const { base } = useSession();
  const run = useAction();
  const [payload, setPayload] = useState(JSON.stringify(definition.trigger.sample_payload ?? {}, null, 2));
  const [result, setResult] = useState<Execution | null>(null);
  const hasLive = workflow.versions.some((v) => v.state === "published");

  async function start(mode: "test" | "live") {
    const parsed = parseJson(payload);
    if (parsed.error) return run.setError(parsed.error);

    if (mode === "live" && !window.confirm("Run the live version now? Real actions will happen (sensitive ones still wait for approval).")) {
      return;
    }

    const execution = await run.run(() =>
      api<Execution>(`${base}/workflows/${workflow.id}/executions`, { body: { mode, payload: parsed.value } }),
    );
    if (execution) {
      setResult(execution);
      onRun(execution);
    }
  }

  return (
    <Card>
      <h2 className="font-semibold">Try it</h2>
      <p className="mt-1 text-sm text-slate-500">
        A <strong>test run</strong> uses the draft and only simulates emails and saves. Nothing real happens.
      </p>
      <Field label="Trigger data (JSON)">
        <textarea
          className={`${inputClass} min-h-40 font-mono text-xs`}
          value={payload}
          onChange={(event) => setPayload(event.target.value)}
        />
      </Field>
      <ErrorNote message={run.error} />
      <div className="mt-3 flex flex-wrap gap-2">
        <Button onClick={() => start("test")} disabled={!canRun || run.busy}>
          {run.busy ? "Running…" : "Test run"}
        </Button>
        <Button variant="secondary" onClick={() => start("live")} disabled={!canRun || run.busy || !hasLive || workflow.status !== "active"}>
          Run live
        </Button>
      </div>
      {result && (
        <div className="mt-4 rounded-lg border border-slate-200 p-3 text-sm">
          <div className="flex items-center justify-between">
            <span>
              Run #{result.id} ({result.mode})
            </span>
            <StatusBadge status={result.status} />
          </div>
          {result.error && <p className="mt-2 text-red-700">{result.error}</p>}
          {result.status === "waiting_approval" && (
            <p className="mt-2 text-amber-800">
              Waiting for approval. <Link href="/approvals" className="underline">Review it</Link>
            </p>
          )}
          <ol className="mt-3 space-y-1">
            {result.steps.map((s) => (
              <li key={s.step_id} className="flex justify-between gap-2">
                <span className="text-slate-700">{s.step_id}</span>
                <StatusBadge status={s.status} />
              </li>
            ))}
          </ol>
          <Link href={`/executions/${result.id}`} className="mt-3 inline-block text-indigo-600 hover:underline">
            Open full run →
          </Link>
        </div>
      )}
    </Card>
  );
}

function EditPanel({
  definition,
  editable,
  actions,
  onSave,
  error,
}: {
  definition: Definition;
  editable: boolean;
  actions: ActionInfo[];
  onSave: (definition: Definition) => Promise<boolean>;
  error: string | null;
}) {
  const [text, setText] = useState(JSON.stringify(definition, null, 2));
  const [parseError, setParseError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  return (
    <Card>
      <h2 className="font-semibold">Steps (advanced)</h2>
      <p className="mt-1 text-sm text-slate-500">
        Edit the definition directly. Saving changes the draft only; the live version stays as it is until you publish.
      </p>
      <textarea
        className={`${inputClass} mt-3 min-h-96 font-mono text-xs`}
        value={text}
        onChange={(event) => {
          setText(event.target.value);
          setSaved(false);
        }}
        readOnly={!editable}
        spellCheck={false}
      />
      <ErrorNote message={parseError ?? error} />
      {editable && (
        <div className="mt-3 flex items-center gap-3">
          <Button
            onClick={async () => {
              const parsed = parseJson(text);
              if (parsed.error) return setParseError(parsed.error);
              setParseError(null);
              setSaved(await onSave(parsed.value as Definition));
            }}
          >
            Save draft
          </Button>
          {saved && <span className="text-sm text-emerald-700">Saved. Publish to make it live.</span>}
        </div>
      )}
      <details className="mt-4 text-sm">
        <summary className="cursor-pointer text-slate-600">Available actions ({actions.length})</summary>
        <ul className="mt-2 space-y-2">
          {actions.map((item) => (
            <li key={item.name}>
              <code className="text-xs font-semibold">{item.name}</code>
              <span className="text-slate-500"> — {item.description}</span>
              <span className="block text-xs text-slate-400">
                inputs: {Object.entries(item.inputs).map(([name, spec]) => `${name}${spec.required ? "" : "?"}`).join(", ")}
              </span>
            </li>
          ))}
        </ul>
      </details>
    </Card>
  );
}

function TriggerPanel({ workflow, definition, editable }: { workflow: Workflow; definition: Definition; editable: boolean }) {
  const { base } = useSession();
  const webhook = useApi<{ url: string; signature_scheme: string; last_called_at: string | null }>(
    definition.trigger.type === "webhook" ? `${base}/workflows/${workflow.id}/webhook` : null,
  );
  const action = useAction();
  const [created, setCreated] = useState<{ url: string; secret: string } | null>(null);

  if (definition.trigger.type !== "webhook") {
    return (
      <Card>
        <h2 className="font-semibold">Trigger: {definition.trigger.type}</h2>
        <p className="mt-1 text-sm text-slate-500">
          {definition.trigger.type === "manual"
            ? "This workflow runs when you start it (or another app calls the API). To let another app start it automatically, set the trigger type to \"webhook\" in Edit steps."
            : `Schedule: ${definition.trigger.schedule}`}
        </p>
      </Card>
    );
  }

  return (
    <Card>
      <h2 className="font-semibold">Webhook trigger</h2>
      <p className="mt-1 text-sm text-slate-500">
        Other apps start this workflow by sending signed JSON to its private URL. Only the published version runs.
      </p>
      {webhook.data && !created && (
        <div className="mt-3 space-y-1 text-sm">
          <p className="break-all font-mono text-xs">{webhook.data.url}</p>
          <p className="text-slate-500">
            Signature: {webhook.data.signature_scheme} · last call {formatTime(webhook.data.last_called_at)}
          </p>
        </div>
      )}
      {created && (
        <div className="mt-3 space-y-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm">
          <p className="font-medium text-amber-900">Copy the secret now. It will not be shown again.</p>
          <p className="break-all font-mono text-xs">URL: {created.url}</p>
          <p className="break-all font-mono text-xs">Secret: {created.secret}</p>
        </div>
      )}
      <ErrorNote message={action.error} />
      {editable && (
        <Button
          className="mt-3"
          variant={webhook.data ? "secondary" : "primary"}
          disabled={action.busy}
          onClick={async () => {
            const result = await action.run(() =>
              api<{ url: string; secret: string }>(`${base}/workflows/${workflow.id}/webhook`, { body: {} }),
            );
            if (result) setCreated(result);
          }}
        >
          {webhook.data ? "Rotate secret" : "Create webhook URL"}
        </Button>
      )}
    </Card>
  );
}

function SettingsPanel({
  workflow,
  editable,
  onSaved,
}: {
  workflow: Workflow;
  editable: boolean;
  onSaved: (workflow: Workflow) => void;
}) {
  const { base } = useSession();
  const action = useAction();
  const [name, setName] = useState(workflow.name);
  const [description, setDescription] = useState(workflow.description);
  const [minutes, setMinutes] = useState(workflow.minutes_saved_per_run);

  return (
    <Card>
      <form
        className="space-y-3"
        onSubmit={async (event) => {
          event.preventDefault();
          const updated = await action.run(() =>
            api<Workflow>(`${base}/workflows/${workflow.id}`, {
              method: "PATCH",
              body: { name, description, minutes_saved_per_run: minutes },
            }),
          );
          if (updated) onSaved(updated);
        }}
      >
        <Field label="Name">
          <input className={inputClass} value={name} onChange={(e) => setName(e.target.value)} disabled={!editable} />
        </Field>
        <Field label="Description">
          <textarea className={inputClass} value={description} onChange={(e) => setDescription(e.target.value)} disabled={!editable} />
        </Field>
        <Field label="Minutes of manual work saved per successful run" hint="Used for the time-saved dashboard.">
          <input
            type="number"
            min={0}
            className={inputClass}
            value={minutes}
            onChange={(e) => setMinutes(Number(e.target.value))}
            disabled={!editable}
          />
        </Field>
        <ErrorNote message={action.error} />
        {editable && <Button type="submit" disabled={action.busy}>Save</Button>}
      </form>
    </Card>
  );
}
