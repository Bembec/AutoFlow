"use client";

import { useMemo, useState } from "react";

import { Button, Card, ErrorNote, Field, inputClass } from "@/components/ui";
import { useFeatures } from "@/lib/features";
import type { ActionInfo, Condition, ConditionGroup, Definition, Step } from "@/lib/types";

const OPERATORS: { value: Condition["op"]; label: string; smart?: boolean }[] = [
  { value: "eq", label: "is" },
  { value: "neq", label: "is not" },
  { value: "contains", label: "contains" },
  { value: "not_contains", label: "doesn't contain", smart: true },
  { value: "exists", label: "has a value" },
  { value: "not_exists", label: "is empty" },
  { value: "gt", label: "is more than", smart: true },
  { value: "gte", label: "is at least", smart: true },
  { value: "lt", label: "is less than", smart: true },
  { value: "lte", label: "is at most", smart: true },
];

// Same list as the backend (engine/definition.py NO_LOOP_ACTIONS)
const NO_LOOP_ACTIONS = new Set([
  "send_email", "smtp_send_email", "compose_email", "ai_classify", "ai_draft_reply", "ai_extract",
  "ai_summarize", "ai_translate", "classify_enquiry", "delay",
]);
const MAX_CONDITIONS = 10;

const AI_ACTIONS = new Set(["ai_extract", "ai_classify", "ai_summarize", "ai_draft_reply", "ai_translate"]);

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value));
}

function uniqueId(base: string, steps: Step[]) {
  const stem = base.replace(/[^a-z0-9_]/g, "_").replace(/^[^a-z]+/, "") || "step";
  let id = stem.slice(0, 40);
  let n = 2;
  while (steps.some((s) => s.id === id)) id = `${stem.slice(0, 40)}_${n++}`;
  return id;
}

/** Data a step can use: trigger fields and outputs of earlier steps. */
function referencesFor(definition: Definition, index: number, actions: ActionInfo[]) {
  const refs = Object.keys(definition.trigger.sample_payload ?? {}).map((key) => ({
    label: `Trigger → ${key}`,
    value: `{{trigger.${key}}}`,
  }));

  definition.steps.slice(0, index).forEach((step) => {
    const action = actions.find((a) => a.name === step.action);
    Object.keys(action?.outputs ?? {}).forEach((output) => {
      refs.push({
        label: `${step.name ?? step.id} → ${output}`,
        value: `{{steps.${step.id}.output.${output}}}`,
      });
    });
  });

  return refs;
}

function displayValue(value: unknown, type: string) {
  if (value === undefined || value === null) return "";
  if (type === "any" && typeof value !== "string") return JSON.stringify(value, null, 2);
  return String(value);
}

function parseValue(text: string, type: string): unknown {
  if (text === "") return undefined;
  if (text.includes("{{")) return text; // a reference stays text
  if (type === "number") return Number.isNaN(Number(text)) ? text : Number(text);
  if (type === "boolean") return text === "true";
  if (type === "any") {
    try {
      return JSON.parse(text);
    } catch {
      return text;
    }
  }
  return text;
}

export function StepEditor({
  definition: saved,
  actions,
  editable,
  selectedStep,
  onSelectStep,
  onSave,
  error,
}: {
  definition: Definition;
  actions: ActionInfo[];
  editable: boolean;
  selectedStep: string | null;
  onSelectStep: (id: string | null) => void;
  onSave: (definition: Definition) => Promise<boolean>;
  error: string | null;
}) {
  const [definition, setDefinition] = useState<Definition>(() => clone(saved));
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [payloadText, setPayloadText] = useState(JSON.stringify(saved.trigger.sample_payload ?? {}, null, 2));
  const [localError, setLocalError] = useState<string | null>(null);

  function change(next: Definition) {
    setDefinition(next);
    setDirty(true);
  }

  function updateStep(index: number, patch: Partial<Step>) {
    const next = clone(definition);
    const previousId = next.steps[index].id;
    next.steps[index] = { ...next.steps[index], ...patch };
    change(next);
    // Keep the renamed step open
    if (patch.id !== undefined && selectedStep === previousId) onSelectStep(patch.id);
  }

  function move(from: number, to: number) {
    if (to < 0 || to >= definition.steps.length || from === to) return;
    const next = clone(definition);
    const [step] = next.steps.splice(from, 1);
    next.steps.splice(to, 0, step);
    change(next);
  }

  function addStep(actionName: string) {
    const action = actions.find((a) => a.name === actionName);
    if (!action) return;
    const next = clone(definition);
    const id = uniqueId(actionName, next.steps);
    const inputs = Object.fromEntries(
      Object.entries(action.inputs)
        .filter(([, spec]) => spec.required)
        .map(([name, spec]) => [name, spec.type === "number" ? 0 : ""]),
    );
    next.steps.push({ id, name: action.description.split(/[.(]/)[0].slice(0, 60), action: actionName, inputs });
    change(next);
    onSelectStep(id);
  }

  async function save() {
    let payload: Record<string, unknown>;
    try {
      payload = JSON.parse(payloadText || "{}");
    } catch {
      setLocalError("The sample trigger data is not valid JSON.");
      return;
    }
    setLocalError(null);
    setSaving(true);
    const next = { ...definition, trigger: { ...definition.trigger, sample_payload: payload } };
    const ok = await onSave(next);
    setSaving(false);
    if (ok) setDirty(false);
  }

  const feature = useFeatures();
  const mcpOn = feature("mcp_tools", false);
  const assistantsOn = feature("ai_assistants", false);
  const grouped = useMemo(() => {
    const groups: Record<string, ActionInfo[]> = { "AI": [], "Apps": [], "Logic & data": [] };
    for (const action of actions) {
      // MCP steps are offered only where MCP tools are switched on
      if (action.connection_provider === "mcp" && !mcpOn) continue;
      if ((action.name === "ai_agent" || action.name === "agent_execute") && !assistantsOn) continue;
      if (action.name.startsWith("ai_") || action.name === "classify_enquiry") groups.AI.push(action);
      else if (action.connection_provider || action.side_effect) groups.Apps.push(action);
      else groups["Logic & data"].push(action);
    }
    return groups;
  }, [actions, mcpOn, assistantsOn]);

  const trigger = definition.trigger;

  return (
    <div className="space-y-4">
      <Card>
        <h2 className="font-semibold">Trigger</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <Field label="Starts when">
            <select
              className={inputClass}
              value={trigger.type}
              disabled={!editable}
              onChange={(e) => change({ ...definition, trigger: { ...trigger, type: e.target.value as Definition["trigger"]["type"] } })}
            >
              <option value="manual">I start it (or via the API)</option>
              <option value="webhook">Another app sends data (webhook)</option>
              <option value="schedule">On a schedule</option>
              <option value="email">An email arrives</option>
              <option value="document">I upload a document (PDF, scan, photo)</option>
            </select>
          </Field>
          {trigger.type === "email" && (
            <>
              <Field label="Mailbox connection" hint="An incoming email (IMAP) connection from Connected apps">
                <input
                  className={inputClass}
                  value={trigger.connection ?? ""}
                  disabled={!editable}
                  onChange={(e) => change({ ...definition, trigger: { ...trigger, connection: e.target.value } })}
                />
              </Field>
              <Field label="Folder">
                <input
                  className={inputClass}
                  value={trigger.folder ?? "INBOX"}
                  disabled={!editable}
                  onChange={(e) => change({ ...definition, trigger: { ...trigger, folder: e.target.value } })}
                />
              </Field>
            </>
          )}
          {trigger.type === "schedule" && (
            <Field label="Schedule (cron, UTC)" hint="e.g. 0 9 * * 1-5 = weekdays at 09:00">
              <input
                className={inputClass}
                value={trigger.schedule ?? ""}
                disabled={!editable}
                onChange={(e) => change({ ...definition, trigger: { ...trigger, schedule: e.target.value } })}
              />
            </Field>
          )}
        </div>
        <Field label="Sample trigger data (JSON)" hint="Used for test runs and to offer trigger fields below.">
          <textarea
            className={`${inputClass} min-h-24 font-mono text-xs`}
            value={payloadText}
            disabled={!editable}
            onChange={(e) => {
              setPayloadText(e.target.value);
              setDirty(true);
              try {
                const parsed = JSON.parse(e.target.value || "{}");
                setDefinition({ ...definition, trigger: { ...trigger, sample_payload: parsed } });
              } catch {
                // keep typing; validated on save
              }
            }}
          />
        </Field>
      </Card>

      <p className="text-sm text-slate-500">
        {editable
          ? "Click a step to change what it does, when it runs, or to repeat it for each item."
          : "Click a step to see its settings."}
      </p>
      <ol className="space-y-2">
        {definition.steps.map((step, index) => {
          const action = actions.find((a) => a.name === step.action);
          const open = selectedStep === step.id;
          return (
            <li
              key={step.id}
              draggable={editable}
              onDragStart={() => setDragIndex(index)}
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => {
                if (dragIndex !== null) move(dragIndex, index);
                setDragIndex(null);
              }}
              className={`rounded-xl border bg-white ${open ? "border-brand-400" : "border-slate-200"} ${dragIndex === index ? "opacity-50" : ""}`}
            >
              <div className="flex items-center gap-2 px-3 py-2">
                {editable && <span className="cursor-grab select-none text-slate-400" title="Drag to reorder">⠿</span>}
                <button
                  className="flex min-w-0 flex-1 flex-wrap items-center gap-x-2 gap-y-1 text-left"
                  aria-expanded={open}
                  onClick={() => onSelectStep(open ? null : step.id)}
                >
                  <span className="text-xs text-slate-400">{index + 1}.</span>
                  <span className="font-medium">{step.name ?? step.id}</span>
                  <span className="text-xs text-slate-500">{step.action.replaceAll("_", " ")}</span>
                  {step.for_each && (
                    <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs text-brand-700">for each item</span>
                  )}
                  {step.when && (
                    <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-800">only if…</span>
                  )}
                  <span className="ml-auto text-xs font-medium text-brand-600">{open ? "Close ▴" : editable ? "Edit ▾" : "View ▾"}</span>
                </button>
                {editable && (
                  <div className="flex gap-1 text-slate-500">
                    <button className="px-1 hover:text-slate-900" onClick={() => move(index, index - 1)} aria-label="Move up">↑</button>
                    <button className="px-1 hover:text-slate-900" onClick={() => move(index, index + 1)} aria-label="Move down">↓</button>
                    <button
                      className="px-1 hover:text-red-600"
                      aria-label="Delete step"
                      onClick={() => {
                        const next = clone(definition);
                        next.steps.splice(index, 1);
                        change(next);
                      }}
                    >
                      ✕
                    </button>
                  </div>
                )}
              </div>

              {open && action && (
                <StepForm
                  step={step}
                  action={action}
                  editable={editable}
                  references={referencesFor(definition, index, actions)}
                  samplePayload={definition.trigger.sample_payload ?? {}}
                  onChange={(patch) => updateStep(index, patch)}
                />
              )}
            </li>
          );
        })}
      </ol>

      {editable && (
        <Card>
          <label className="text-sm font-medium" htmlFor="add-step">Add a step</label>
          <select
            id="add-step"
            className={`${inputClass} mt-1`}
            value=""
            onChange={(e) => e.target.value && addStep(e.target.value)}
          >
            <option value="">Choose what should happen next…</option>
            {Object.entries(grouped).map(([group, items]) => (
              <optgroup key={group} label={group}>
                {items.map((action) => (
                  <option key={action.name} value={action.name}>
                    {action.name.replaceAll("_", " ")}: {action.description}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </Card>
      )}

      <ErrorNote message={localError ?? error} />
      {editable && (
        <div className="flex items-center gap-3">
          <Button onClick={save} disabled={!dirty || saving || definition.steps.length === 0}>
            {saving ? "Saving…" : "Save draft"}
          </Button>
          {dirty ? (
            <span className="text-sm text-amber-700">Unsaved changes</span>
          ) : (
            <span className="text-sm text-slate-500">Saved. Publish to make the draft live.</span>
          )}
        </div>
      )}
    </div>
  );
}

function StepForm({
  step,
  action,
  editable,
  references: earlier,
  samplePayload,
  onChange,
}: {
  step: Step;
  action: ActionInfo;
  editable: boolean;
  references: { label: string; value: string }[];
  samplePayload: Record<string, unknown>;
  onChange: (patch: Partial<Step>) => void;
}) {
  const feature = useFeatures();
  const smart = feature("smarter_logic", false);
  const canLoop = !NO_LOOP_ACTIONS.has(step.action) && !action.requires_approval;
  // Inside a loop, inputs can also use the current item and its position
  const references = step.for_each ? [...loopReferences(step.for_each, samplePayload), ...earlier] : earlier;

  const setInput = (name: string, value: unknown) => {
    const inputs = { ...step.inputs };
    if (value === undefined) delete inputs[name];
    else inputs[name] = value;
    onChange({ inputs });
  };

  return (
    <div className="space-y-4 border-t border-slate-100 px-3 py-3">
      <p className="text-sm text-slate-500">{action.description}</p>

      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Step name">
          <input className={inputClass} value={step.name ?? ""} disabled={!editable} onChange={(e) => onChange({ name: e.target.value })} />
        </Field>
        <Field label="Step id" hint="Lowercase letters, numbers, _. Later steps use it to refer to this one.">
          <input
            className={`${inputClass} font-mono`}
            value={step.id}
            disabled={!editable}
            onChange={(e) => onChange({ id: e.target.value.toLowerCase() })}
          />
        </Field>
      </div>

      {Object.entries(action.inputs).map(([name, spec]) => {
        const value = displayValue(step.inputs[name], spec.type);
        const multiline = spec.type === "any" || name === "body" || name === "text" || name === "message";
        return (
          <div key={name}>
            <div className="flex items-center justify-between gap-2">
              <label htmlFor={`${step.id}-${name}`} className="text-sm font-medium text-slate-700">
                {name.replaceAll("_", " ")}
                {!spec.required && <span className="font-normal text-slate-400"> (optional)</span>}
              </label>
              {editable && references.length > 0 && (
                <select
                  className="max-w-56 rounded border border-slate-200 px-1 py-0.5 text-xs text-slate-600"
                  value=""
                  aria-label={`Insert data into ${name}`}
                  onChange={(e) => {
                    if (!e.target.value) return;
                    const current = typeof step.inputs[name] === "string" ? (step.inputs[name] as string) : "";
                    setInput(name, current ? `${current}${e.target.value}` : e.target.value);
                  }}
                >
                  <option value="">+ insert data from…</option>
                  {references.map((ref) => <option key={ref.value} value={ref.value}>{ref.label}</option>)}
                </select>
              )}
            </div>
            {spec.description && <p className="text-xs text-slate-500">{spec.description}</p>}
            {multiline ? (
              <textarea
                id={`${step.id}-${name}`}
                aria-label={name.replaceAll("_", " ")}
                className={`${inputClass} mt-1 min-h-20 font-mono text-xs`}
                value={value}
                disabled={!editable}
                onChange={(e) => setInput(name, parseValue(e.target.value, spec.type))}
              />
            ) : (
              <input
                id={`${step.id}-${name}`}
                aria-label={name.replaceAll("_", " ")}
                className={`${inputClass} mt-1`}
                value={value}
                disabled={!editable}
                onChange={(e) => setInput(name, parseValue(e.target.value, spec.type))}
              />
            )}
          </div>
        );
      })}

      {(smart || step.for_each) && canLoop && (
        <details open={Boolean(step.for_each)} className="rounded-lg bg-slate-50 p-3">
          <summary className="cursor-pointer text-sm font-medium">Repeat for each item…</summary>
          <Field label="Run this step once for every item in" hint="For example the order's line items. Up to 100 items; finished items are never repeated.">
            <select
              className={inputClass}
              disabled={!editable}
              value={step.for_each ?? ""}
              onChange={(e) => onChange({ for_each: e.target.value || undefined })}
            >
              <option value="">Run once (no loop)</option>
              {earlier.map((ref) => <option key={ref.value} value={ref.value}>{ref.label}</option>)}
            </select>
          </Field>
        </details>
      )}

      {smart ? (
        <ConditionEditor step={step} editable={editable} references={earlier} onChange={onChange} />
      ) : (
      <details open={Boolean(step.when)} className="rounded-lg bg-slate-50 p-3">
        <summary className="cursor-pointer text-sm font-medium">Only run if…</summary>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
          <select
            className={`${inputClass} w-auto`}
            disabled={!editable}
            value={step.when && "left" in step.when && typeof step.when.left === "string" ? step.when.left : ""}
            onChange={(e) =>
              onChange({
                when: e.target.value
                  ? { ...(step.when && "op" in step.when ? step.when : { op: "eq" as const, right: "" }), left: e.target.value }
                  : undefined,
              })
            }
          >
            <option value="">Always run</option>
            {references.map((ref) => <option key={ref.value} value={ref.value}>{ref.label}</option>)}
          </select>
          {step.when && "op" in step.when && (
            <>
              <select
                className={`${inputClass} w-auto`}
                disabled={!editable}
                value={step.when.op}
                onChange={(e) => onChange({ when: { ...(step.when as Condition), op: e.target.value as Condition["op"] } })}
              >
                {OPERATORS.filter((op) => !op.smart).map((op) => <option key={op.value} value={op.value}>{op.label}</option>)}
              </select>
              {!["exists", "not_exists"].includes(step.when.op) && (
                <input
                  className={`${inputClass} w-40`}
                  disabled={!editable}
                  value={String(step.when.right ?? "")}
                  onChange={(e) => onChange({ when: { ...(step.when as Condition), right: e.target.value } })}
                />
              )}
            </>
          )}
        </div>
      </details>
      )}

      <details className="rounded-lg bg-slate-50 p-3">
        <summary className="cursor-pointer text-sm font-medium">Reliability & safety</summary>
        <div className="mt-2 grid gap-3 sm:grid-cols-3">
          <Field label="Attempts" hint="1–5">
            <input
              type="number" min={1} max={5}
              className={inputClass}
              disabled={!editable}
              value={step.retry?.max_attempts ?? 1}
              onChange={(e) => onChange({ retry: { backoff_seconds: step.retry?.backoff_seconds ?? 1, max_attempts: Number(e.target.value) } })}
            />
          </Field>
          <Field label="Wait between tries (s)">
            <input
              type="number" min={0} max={60}
              className={inputClass}
              disabled={!editable}
              value={step.retry?.backoff_seconds ?? 1}
              onChange={(e) => onChange({ retry: { max_attempts: step.retry?.max_attempts ?? 1, backoff_seconds: Number(e.target.value) } })}
            />
          </Field>
          <Field label="Time limit (s)">
            <input
              type="number" min={1} max={300}
              className={inputClass}
              disabled={!editable}
              value={step.timeout_seconds ?? 30}
              onChange={(e) => onChange({ timeout_seconds: Number(e.target.value) })}
            />
          </Field>
        </div>
        <label className="mt-3 flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            disabled={!editable || action.requires_approval}
            checked={action.requires_approval || Boolean(step.requires_approval)}
            onChange={(e) => onChange({ requires_approval: e.target.checked || undefined })}
          />
          A person approves this step before it runs
          {action.requires_approval && <span className="text-xs text-slate-500">(always, for this action)</span>}
        </label>
        {AI_ACTIONS.has(step.action) && (
          <Field label="Send to review below this confidence (0–1)" hint="0 = never. Possible prompt injections are always reviewed.">
            <input
              type="number" min={0} max={1} step={0.05}
              className={`${inputClass} w-32`}
              disabled={!editable}
              value={step.review_below_confidence ?? ""}
              placeholder="default"
              onChange={(e) => onChange({ review_below_confidence: e.target.value === "" ? undefined : Number(e.target.value) })}
            />
          </Field>
        )}
      </details>
    </div>
  );
}

/** {{item…}} and {{index}} choices for a loop over a trigger list. */
function loopReferences(forEach: string, sample: Record<string, unknown>) {
  const refs = [
    { label: "Current item", value: "{{item}}" },
    { label: "Item number (from 0)", value: "{{index}}" },
  ];
  const path = forEach.match(/\{\{\s*trigger\.([\w.]+)\s*\}\}/)?.[1];
  let list: unknown = sample;
  for (const part of path ? path.split(".") : []) {
    list = list && typeof list === "object" ? (list as Record<string, unknown>)[part] : undefined;
  }
  const first = Array.isArray(list) ? list[0] : undefined;
  if (first && typeof first === "object") {
    Object.keys(first).forEach((key) => refs.push({ label: `Item → ${key}`, value: `{{item.${key}}}` }));
  }
  return refs;
}

type Mode = "all" | "any";

/** Plain conditions of the step's `when`, or null when it nests groups (edited as JSON). */
function flatten(when: Step["when"]): { mode: Mode; conditions: Condition[] } | null {
  if (!when) return { mode: "all", conditions: [] };
  if ("op" in when) return { mode: "all", conditions: [when as Condition] };
  const group = when as ConditionGroup;
  const mode: Mode = group.any ? "any" : "all";
  const parts = group.any ?? group.all ?? [];
  return parts.every((part) => "op" in part) ? { mode, conditions: parts as Condition[] } : null;
}

function ConditionEditor({
  step,
  editable,
  references,
  onChange,
}: {
  step: Step;
  editable: boolean;
  references: { label: string; value: string }[];
  onChange: (patch: Partial<Step>) => void;
}) {
  const flat = flatten(step.when);

  if (flat === null) {
    return (
      <p className="rounded-lg bg-slate-50 p-3 text-sm text-slate-600">
        This step has nested AND/OR groups. Edit them in the workflow definition.
      </p>
    );
  }

  const save = (mode: Mode, conditions: Condition[]) => {
    if (conditions.length === 0) onChange({ when: undefined });
    else if (conditions.length === 1) onChange({ when: conditions[0] });
    else onChange({ when: mode === "all" ? { all: conditions } : { any: conditions } });
  };
  const update = (index: number, patch: Partial<Condition>) =>
    save(flat.mode, flat.conditions.map((condition, i) => (i === index ? { ...condition, ...patch } : condition)));

  return (
    <details open={flat.conditions.length > 0} className="rounded-lg bg-slate-50 p-3">
      <summary className="cursor-pointer text-sm font-medium">Only run if…</summary>
      <div className="mt-2 space-y-2 text-sm">
        {flat.conditions.length > 1 && (
          <label className="flex items-center gap-2">
            Run when
            <select
              className={`${inputClass} w-auto`}
              disabled={!editable}
              value={flat.mode}
              onChange={(e) => save(e.target.value as Mode, flat.conditions)}
            >
              <option value="all">all of these are true</option>
              <option value="any">any of these is true</option>
            </select>
          </label>
        )}
        {flat.conditions.map((condition, index) => (
          <div key={index} className="flex flex-wrap items-center gap-2">
            <select
              className={`${inputClass} w-auto`}
              aria-label="Value to check"
              disabled={!editable}
              value={typeof condition.left === "string" ? condition.left : ""}
              onChange={(e) => update(index, { left: e.target.value })}
            >
              {references.map((ref) => <option key={ref.value} value={ref.value}>{ref.label}</option>)}
            </select>
            <select
              className={`${inputClass} w-auto`}
              aria-label="Comparison"
              disabled={!editable}
              value={condition.op}
              onChange={(e) => update(index, { op: e.target.value as Condition["op"] })}
            >
              {OPERATORS.map((op) => <option key={op.value} value={op.value}>{op.label}</option>)}
            </select>
            {!["exists", "not_exists"].includes(condition.op) && (
              <input
                className={`${inputClass} w-36`}
                aria-label="Compare with"
                disabled={!editable}
                value={String(condition.right ?? "")}
                onChange={(e) => update(index, { right: e.target.value })}
              />
            )}
            {editable && (
              <button
                type="button"
                className="px-1 text-slate-400 hover:text-red-600"
                aria-label="Remove condition"
                onClick={() => save(flat.mode, flat.conditions.filter((_, i) => i !== index))}
              >
                ✕
              </button>
            )}
          </div>
        ))}
        {editable && references.length > 0 && flat.conditions.length < MAX_CONDITIONS && (
          <Button
            type="button"
            variant="ghost"
            className="px-0 text-xs"
            onClick={() => save(flat.mode, [...flat.conditions, { left: references[0].value, op: "eq", right: "" }])}
          >
            {flat.conditions.length === 0 ? "+ Add a condition" : "+ Add another condition"}
          </Button>
        )}
      </div>
    </details>
  );
}
