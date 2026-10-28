"use client";

import { useState } from "react";

import { Button, Card, ErrorNote, Field, Loading, PageHeader, formatTime, inputClass } from "@/components/ui";
import { api } from "@/lib/api";
import { useFeatures } from "@/lib/features";
import { useSession } from "@/lib/session";
import { T, useI18n } from "@/lib/i18n";
import type { BusinessProfile, Connection, Member, NotificationSettings, Policies, Role } from "@/lib/types";
import { useAction, useApi } from "@/lib/useApi";

export default function SettingsPage() {
  const { workspace } = useSession();
  const { t } = useI18n();

  return (
    <>
      <PageHeader title={t("set.title")} description={`Workspace “${workspace.name}” · your role: ${workspace.role}`} />
      <div className="grid gap-6 xl:grid-cols-2">
        <div className="space-y-6">
          <EmergencyStop />
          <TwoFactorCard />
          <NotificationsCard />
          <PoliciesCard />
        </div>
        <div className="space-y-6">
          <BusinessCard />
          <MembersCard />
          <AssistantAccessCard />
          <AuditCard />
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
      <h2 className="font-semibold"><T k="set.emergency" /></h2>
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
            <T k="set.resumeAll" />
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
            <T k="set.stopAll" />
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
      <h2 className="font-semibold"><T k="set.limits" /></h2>
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
            <strong>Approve everything.</strong> Every action that changes something outside Luphina (saving, sending, posting) waits for a person, not just emails.
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
      <h2 className="font-semibold"><T k="set.team" /></h2>
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

function TwoFactorCard() {
  const { data, reload } = useApi<{ enabled: boolean; recovery_codes_left: number }>("/auth/2fa");
  const { data: activity } = useApi<{ action: string; ip: string | null; created_at: string }[]>("/auth/activity");
  const action = useAction();
  const [setup, setSetup] = useState<{ secret: string; otpauth_uri: string } | null>(null);
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [recovery, setRecovery] = useState<string[] | null>(null);

  if (!data) return null;

  return (
    <Card>
      <h2 className="font-semibold"><T k="set.twoFactor" /></h2>
      <p className="mt-1 text-sm text-slate-500">
        {data.enabled
          ? `On. Sign-in also asks for a code from your authenticator app. ${data.recovery_codes_left} recovery codes left.`
          : "Protect your account with a code from an authenticator app (Google Authenticator, Authy, 1Password…)."}
      </p>

      {recovery && (
        <div className="mt-3 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm">
          <p className="font-medium text-amber-900">Save these recovery codes now. Each works once if you lose your phone. They will not be shown again.</p>
          <ul className="mt-2 grid grid-cols-2 gap-1 font-mono">{recovery.map((c) => <li key={c}>{c}</li>)}</ul>
        </div>
      )}

      {!data.enabled && !setup && (
        <Button
          className="mt-3"
          disabled={action.busy}
          onClick={async () => {
            const result = await action.run(() => api<{ secret: string; otpauth_uri: string }>("/auth/2fa/setup", { body: {} }));
            if (result) setSetup(result);
          }}
        >
          Set up two-factor login
        </Button>
      )}

      {!data.enabled && setup && (
        <form
          className="mt-3 space-y-3"
          onSubmit={async (event) => {
            event.preventDefault();
            const result = await action.run(() => api<{ recovery_codes: string[] }>("/auth/2fa/enable", { body: { code } }));
            if (result) {
              setRecovery(result.recovery_codes);
              setSetup(null);
              setCode("");
              reload();
            }
          }}
        >
          <p className="text-sm">
            1. In your authenticator app, add an account with this key (or{" "}
            <a href={setup.otpauth_uri} className="text-brand-600 underline">open it on this phone</a>):
          </p>
          <p className="break-all rounded bg-slate-100 px-2 py-1 font-mono text-sm">{setup.secret}</p>
          <Field label="2. Enter the 6-digit code it shows">
            <input className={`${inputClass} tracking-widest`} inputMode="numeric" autoComplete="one-time-code"
              value={code} onChange={(e) => setCode(e.target.value)} required />
          </Field>
          <Button type="submit" disabled={action.busy}>Turn on</Button>
        </form>
      )}

      {data.enabled && (
        <details className="mt-3 text-sm">
          <summary className="cursor-pointer text-slate-600">Turn off two-factor login</summary>
          <form
            className="mt-2 space-y-2"
            onSubmit={async (event) => {
              event.preventDefault();
              const done = await action.run(() => api("/auth/2fa/disable", { body: { password, code } }));
              if (done) {
                setPassword("");
                setCode("");
                setRecovery(null);
                reload();
              }
            }}
          >
            <input className={inputClass} type="password" placeholder="Password" autoComplete="current-password"
              value={password} onChange={(e) => setPassword(e.target.value)} required />
            <input className={inputClass} placeholder="Authenticator or recovery code" autoComplete="one-time-code"
              value={code} onChange={(e) => setCode(e.target.value)} required />
            <Button type="submit" variant="danger" disabled={action.busy}>Turn off</Button>
          </form>
        </details>
      )}

      <ErrorNote message={action.error} />

      {activity && activity.length > 0 && (
        <details className="mt-3 text-sm">
          <summary className="cursor-pointer text-slate-600">Recent sign-ins</summary>
          <ul className="mt-2 space-y-1 text-xs text-slate-600">
            {activity.slice(0, 10).map((a, i) => (
              <li key={i} className={a.action === "auth.login_failed" ? "text-red-700" : ""}>
                {formatTime(a.created_at)} · {a.action.replace("auth.", "").replaceAll("_", " ")} · {a.ip ?? "—"}
              </li>
            ))}
          </ul>
        </details>
      )}
    </Card>
  );
}

function AuditCard() {
  const { base, can } = useSession();
  const { data } = useApi<{ id: number; action: string; user: string | null; target: string | null; created_at: string }[]>(
    can("admin") ? `${base}/audit` : null,
  );

  if (!can("admin") || !data) return null;

  return (
    <Card>
      <h2 className="font-semibold"><T k="set.activity" /></h2>
      <p className="mt-1 text-sm text-slate-500">Who changed what in this workspace.</p>
      {data.length === 0 ? (
        <p className="mt-3 text-sm text-slate-500">Nothing recorded yet.</p>
      ) : (
        <ul className="mt-3 max-h-80 divide-y divide-slate-100 overflow-auto text-sm">
          {data.map((event) => (
            <li key={event.id} className="py-2">
              <span className="font-medium">{event.action.replace(".", ": ").replaceAll("_", " ")}</span>
              {event.target && <span className="text-slate-600"> · {event.target}</span>}
              <span className="block text-xs text-slate-500">
                {event.user ?? "system"} · {formatTime(event.created_at)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function NotificationsCard() {
  const { base } = useSession();
  const { data, error, loading, setData } = useApi<NotificationSettings>(`${base}/notifications`);
  const { data: connections } = useApi<Connection[]>(`${base}/connections`);

  if (loading && !data) return <Loading />;
  if (!data) return <ErrorNote message={error} />;

  return (
    <NotificationsForm key={JSON.stringify(data)} data={data} connections={connections ?? []} onSaved={setData} />
  );
}

function NotificationsForm({
  data,
  connections,
  onSaved,
}: {
  data: NotificationSettings;
  connections: Connection[];
  onSaved: (settings: NotificationSettings) => void;
}) {
  const { base, can } = useSession();
  const action = useAction();
  const [form, setForm] = useState<NotificationSettings>(data);
  const [sent, setSent] = useState(false);
  const editable = can("admin");
  const named = (provider: string) => connections.filter((c) => c.provider === provider);

  return (
    <Card id="notifications">
      <h2 className="font-semibold"><T k="set.notifications" /></h2>
      <p className="mt-1 text-sm text-slate-500">
        Hear about it when something needs you, instead of checking the app. Sent by the background worker.
      </p>
      <form
        className="mt-3 space-y-3"
        onSubmit={async (event) => {
          event.preventDefault();
          const saved = await action.run(() =>
            api<NotificationSettings>(`${base}/notifications`, { method: "PATCH", body: form }),
          );
          if (saved) onSaved(saved);
        }}
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Email me at">
            <input
              type="email"
              className={inputClass}
              value={form.notify_email ?? ""}
              onChange={(e) => setForm({ ...form, notify_email: e.target.value })}
              disabled={!editable}
            />
          </Field>
          <Field label="Send email with" hint="An Email (SMTP) connection">
            <select
              className={inputClass}
              value={form.notify_smtp_connection ?? ""}
              onChange={(e) => setForm({ ...form, notify_smtp_connection: e.target.value })}
              disabled={!editable}
            >
              <option value="">— none —</option>
              {named("smtp").map((c) => <option key={c.id} value={c.name}>{c.name}</option>)}
            </select>
          </Field>
        </div>
        <Field label="Post to Slack with" hint="A Slack connection (incoming webhook)">
          <select
            className={inputClass}
            value={form.notify_slack_connection ?? ""}
            onChange={(e) => setForm({ ...form, notify_slack_connection: e.target.value })}
            disabled={!editable}
          >
            <option value="">— none —</option>
            {named("slack").map((c) => <option key={c.id} value={c.name}>{c.name}</option>)}
          </select>
        </Field>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.notify_on_approval}
            onChange={(e) => setForm({ ...form, notify_on_approval: e.target.checked })}
            disabled={!editable}
          />
          Something waits for my approval
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.notify_on_failure}
            onChange={(e) => setForm({ ...form, notify_on_failure: e.target.checked })}
            disabled={!editable}
          />
          A live run fails or needs attention
        </label>
        <ErrorNote message={action.error} />
        {editable && (
          <div className="flex flex-wrap items-center gap-2">
            <Button type="submit" disabled={action.busy}>Save</Button>
            <Button
              type="button"
              variant="secondary"
              disabled={action.busy}
              onClick={async () => {
                setSent(false);
                const result = await action.run(() => api(`${base}/notifications/test`, { body: {} }));
                if (result) setSent(true);
              }}
            >
              Send a test
            </Button>
            {sent && <span className="text-sm text-emerald-700">Queued, so it should arrive in a few seconds.</span>}
          </div>
        )}
      </form>
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
    <Card id="business">
      <h2 className="font-semibold"><T k="set.business" /></h2>
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
      <h2 className="font-semibold"><T k="set.newWorkspace" /></h2>
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

interface ApiKeyInfo {
  id: number;
  name: string;
  prefix: string;
  created_at: string;
  last_used_at: string | null;
  revoked: boolean;
}

/** Keys that let outside AI assistants use opted-in workflows (MCP). */
function AssistantAccessCard() {
  const { base, can } = useSession();
  const { t } = useI18n();
  const feature = useFeatures();
  const enabled = feature("mcp_server", false) && can("admin");
  const { data, reload } = useApi<{ server_url: string; keys: ApiKeyInfo[] }>(enabled ? `${base}/api-keys` : null);
  const action = useAction();
  const [name, setName] = useState("");
  const [created, setCreated] = useState<string | null>(null);

  if (!enabled) return null;

  return (
    <Card>
      <h2 className="font-semibold">{t("mcp.title")}</h2>
      <p className="mt-1 text-sm text-slate-500">{t("mcp.about")}</p>
      {data && (
        <p className="mt-3 text-sm">
          {t("mcp.server")}: <code className="break-all rounded bg-slate-100 px-1.5 py-0.5">{data.server_url}</code>
        </p>
      )}
      {created && (
        <div role="status" className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          {t("mcp.copyNow")} <code className="block break-all pt-1 font-mono">{created}</code>
        </div>
      )}
      <ul className="mt-3 divide-y divide-slate-100 text-sm">
        {data?.keys.map((key) => (
          <li key={key.id} className="flex items-center justify-between gap-2 py-2">
            <span>
              <span className="font-medium">{key.name}</span>{" "}
              <code className="text-xs text-slate-500">{key.prefix}…</code>
              <span className="block text-xs text-slate-500">
                {key.revoked ? t("mcp.revoked") : key.last_used_at ? t("mcp.lastUsed", { time: formatTime(key.last_used_at) }) : ""}
              </span>
            </span>
            {!key.revoked && (
              <Button
                variant="ghost"
                className="px-2 py-1 text-xs text-red-600"
                disabled={action.busy}
                onClick={async () => {
                  await action.run(() => api(`${base}/api-keys/${key.id}`, { method: "DELETE" }));
                  reload();
                }}
              >
                {t("mcp.revoke")}
              </Button>
            )}
          </li>
        ))}
      </ul>
      <form
        className="mt-3 flex flex-wrap items-end gap-2"
        onSubmit={async (event) => {
          event.preventDefault();
          const result = await action.run(() => api<{ key: string }>(`${base}/api-keys`, { body: { name } }));
          if (result) {
            setCreated(result.key);
            setName("");
            reload();
          }
        }}
      >
        <Field label={t("mcp.keyName")}>
          <input className={inputClass} value={name} onChange={(e) => setName(e.target.value)} required maxLength={100} />
        </Field>
        <Button type="submit" variant="secondary" disabled={action.busy}>{t("mcp.create")}</Button>
      </form>
      <ErrorNote message={action.error} />
    </Card>
  );
}

