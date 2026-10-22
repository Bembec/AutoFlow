"use client";

import { useState } from "react";

import { Button, Card, ErrorNote, Field, Loading, PageHeader, inputClass } from "@/components/ui";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";
import type { BusinessProfile, Member, Policies, Role } from "@/lib/types";
import { useAction, useApi } from "@/lib/useApi";

export default function SettingsPage() {
  const { workspace } = useSession();

  return (
    <>
      <PageHeader title="Settings" description={`Workspace “${workspace.name}” · your role: ${workspace.role}`} />
      <div className="grid gap-6 xl:grid-cols-2">
        <div className="space-y-6">
          <EmergencyStop />
          <PoliciesCard />
        </div>
        <div className="space-y-6">
          <BusinessCard />
          <MembersCard />
          <NewWorkspaceCard />
        </div>
      </div>
    </>
  );
}

function EmergencyStop() {
  const { base, can } = useSession();
  const { data, reload } = useApi<Policies>(`${base}/policies`);
  const action = useAction();

  if (!data) return null;

  return (
    <Card className={data.automation_paused ? "border-red-300" : ""}>
      <h2 className="font-semibold">Emergency stop</h2>
      <p className="mt-1 text-sm text-slate-500">
        Stops every workflow in this workspace at once, cancels runs in progress and blocks webhooks until you resume.
      </p>
      <ErrorNote message={action.error} />
      {can("admin") ? (
        data.automation_paused ? (
          <Button
            className="mt-3"
            disabled={action.busy}
            onClick={async () => {
              await action.run(() => api(`${base}/resume-automations`, { body: {} }));
              window.location.reload();
            }}
          >
            Resume all automations
          </Button>
        ) : (
          <Button
            className="mt-3"
            variant="danger"
            disabled={action.busy}
            onClick={async () => {
              const reason = window.prompt("Stop all automations now? Optional reason:");
              if (reason === null) return;
              await action.run(() => api(`${base}/emergency-stop`, { body: { reason: reason || null } }));
              reload();
              window.location.reload();
            }}
          >
            Stop all automations
          </Button>
        )
      ) : (
        <p className="mt-3 text-sm text-slate-500">Ask an admin to use the emergency stop.</p>
      )}
    </Card>
  );
}

function PoliciesCard() {
  const { base } = useSession();
  const { data, error, loading, setData } = useApi<Policies>(`${base}/policies`);

  if (loading && !data) return <Loading />;
  if (!data) return <ErrorNote message={error} />;

  // Remount the form whenever saved values change
  return <PoliciesForm key={JSON.stringify(data)} data={data} onSaved={setData} />;
}

function PoliciesForm({ data, onSaved }: { data: Policies; onSaved: (policies: Policies) => void }) {
  const { base, can } = useSession();
  const action = useAction();
  const [form, setForm] = useState<Partial<Policies>>(data);

  const editable = can("admin");
  const number = (key: keyof Policies) => (event: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [key]: Number(event.target.value) });

  return (
    <Card>
      <h2 className="font-semibold">Safety limits</h2>
      <p className="mt-1 text-sm text-slate-500">Daily caps protect you from a runaway workflow spending money or emailing too many people.</p>
      <form
        className="mt-4 space-y-3"
        onSubmit={async (event) => {
          event.preventDefault();
          const updated = await action.run(() =>
            api<Policies>(`${base}/policies`, {
              method: "PATCH",
              body: {
                max_executions_per_day: form.max_executions_per_day,
                max_ai_calls_per_day: form.max_ai_calls_per_day,
                max_emails_per_day: form.max_emails_per_day,
                approve_all_side_effects: form.approve_all_side_effects,
              },
            }),
          );
          if (updated) onSaved(updated);
        }}
      >
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label={`Runs/day (used ${data.usage_today.executions})`}>
            <input type="number" min={0} className={inputClass} value={form.max_executions_per_day ?? 0} onChange={number("max_executions_per_day")} disabled={!editable} />
          </Field>
          <Field label={`AI calls/day (used ${data.usage_today.ai_calls})`}>
            <input type="number" min={0} className={inputClass} value={form.max_ai_calls_per_day ?? 0} onChange={number("max_ai_calls_per_day")} disabled={!editable} />
          </Field>
          <Field label={`Emails/day (sent ${data.usage_today.emails})`}>
            <input type="number" min={0} className={inputClass} value={form.max_emails_per_day ?? 0} onChange={number("max_emails_per_day")} disabled={!editable} />
          </Field>
        </div>
        <label className="flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            className="mt-1"
            checked={Boolean(form.approve_all_side_effects)}
            onChange={(event) => setForm({ ...form, approve_all_side_effects: event.target.checked })}
            disabled={!editable}
          />
          <span>
            <strong>Approve everything.</strong> Every action that changes something outside AutoFlow (saving, sending, posting) waits for a person, not just emails.
          </span>
        </label>
        <ErrorNote message={action.error} />
        {editable && <Button type="submit" disabled={action.busy}>Save limits</Button>}
      </form>
    </Card>
  );
}

function MembersCard() {
  const { base, can } = useSession();
  const { data, reload } = useApi<Member[]>(`${base}/members`);
  const action = useAction();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>("member");

  return (
    <Card>
      <h2 className="font-semibold">Team</h2>
      <ul className="mt-3 divide-y divide-slate-100 text-sm">
        {data?.map((member) => (
          <li key={member.user_id} className="flex justify-between py-2">
            <span>
              {member.name} <span className="text-slate-500">{member.email}</span>
            </span>
            <span className="text-slate-500">{member.role}</span>
          </li>
        ))}
      </ul>
      {can("admin") && (
        <form
          className="mt-4 flex flex-wrap items-end gap-2"
          onSubmit={async (event) => {
            event.preventDefault();
            const done = await action.run(() => api(`${base}/members`, { body: { email, role } }));
            if (done) {
              setEmail("");
              reload();
            }
          }}
        >
          <div className="min-w-48 flex-1">
            <Field label="Add a teammate (they need an account)">
              <input type="email" className={inputClass} value={email} onChange={(e) => setEmail(e.target.value)} required />
            </Field>
          </div>
          <select className={`${inputClass} w-auto`} value={role} onChange={(e) => setRole(e.target.value as Role)} aria-label="Role">
            <option value="viewer">viewer</option>
            <option value="member">member</option>
            <option value="admin">admin</option>
          </select>
          <Button type="submit" disabled={action.busy}>Add</Button>
        </form>
      )}
      <ErrorNote message={action.error} />
    </Card>
  );
}

function BusinessCard() {
  const { base } = useSession();
  const { data, error, loading, setData } = useApi<BusinessProfile>(`${base}/business`);

  if (loading && !data) return <Loading />;
  if (!data) return <ErrorNote message={error} />;

  // Remount the form whenever saved values change
  return <BusinessForm key={JSON.stringify(data)} data={data} onSaved={setData} />;
}

function BusinessForm({ data, onSaved }: { data: BusinessProfile; onSaved: (profile: BusinessProfile) => void }) {
  const { base, can } = useSession();
  const action = useAction();
  const [form, setForm] = useState<BusinessProfile>(data);
  const editable = can("admin");
  const set = (key: keyof BusinessProfile) =>
    (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setForm({ ...form, [key]: event.target.value });

  return (
    <Card>
      <h2 className="font-semibold">Business details</h2>
      <p className="mt-1 text-sm text-slate-500">Printed on the invoices your workflows create.</p>
      <form
        className="mt-3 space-y-3"
        onSubmit={async (event) => {
          event.preventDefault();
          const saved = await action.run(() =>
            api<BusinessProfile>(`${base}/business`, { method: "PATCH", body: form }),
          );
          if (saved) onSaved(saved);
        }}
      >
        <Field label="Business name">
          <input className={inputClass} value={form.business_name ?? ""} onChange={set("business_name")} disabled={!editable} />
        </Field>
        <Field label="Address">
          <textarea className={inputClass} value={form.business_address ?? ""} onChange={set("business_address")} disabled={!editable} />
        </Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Tax / VAT number">
            <input className={inputClass} value={form.tax_id ?? ""} onChange={set("tax_id")} disabled={!editable} />
          </Field>
          <Field label="Invoice number prefix" hint="e.g. INV- gives INV-00001">
            <input className={inputClass} value={form.invoice_prefix} onChange={set("invoice_prefix")} disabled={!editable} />
          </Field>
        </div>
        <ErrorNote message={action.error} />
        {editable && <Button type="submit" disabled={action.busy}>Save details</Button>}
      </form>
    </Card>
  );
}

function NewWorkspaceCard() {
  const { refresh, switchWorkspace } = useSession();
  const action = useAction();
  const [name, setName] = useState("");

  return (
    <Card>
      <h2 className="font-semibold">New workspace</h2>
      <p className="mt-1 text-sm text-slate-500">Each workspace keeps its own workflows, data and connected apps separate.</p>
      <form
        className="mt-3 flex gap-2"
        onSubmit={async (event) => {
          event.preventDefault();
          const workspace = await action.run(() => api<{ id: number }>("/workspaces", { body: { name } }));
          if (workspace) {
            await refresh();
            switchWorkspace(workspace.id);
          }
        }}
      >
        <input className={inputClass} placeholder="e.g. Second shop" value={name} onChange={(e) => setName(e.target.value)} required />
        <Button type="submit" disabled={action.busy}>Create</Button>
      </form>
      <ErrorNote message={action.error} />
    </Card>
  );
}
