"use client";

import { Plug } from "lucide-react";
import { useState } from "react";

import { Button, Card, EmptyState, ErrorNote, Field, Loading, PageHeader, StatusBadge, formatTime, inputClass } from "@/components/ui";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";
import { useI18n } from "@/lib/i18n";
import type { Connection, IntegrationInfo } from "@/lib/types";
import { useAction, useApi } from "@/lib/useApi";

export default function ConnectionsPage() {
  const { base, can } = useSession();
  const { t } = useI18n();
  const { data: connections, error, loading, reload } = useApi<Connection[]>(`${base}/connections`);
  const { data: integrations } = useApi<IntegrationInfo[]>("/integrations");
  const [adding, setAdding] = useState<IntegrationInfo | null>(null);
  const action = useAction();

  return (
    <>
      <PageHeader
        title={t("conn.title")}
        description={t("conn.subtitle")}
      />
      <ErrorNote message={error ?? action.error} />

      {can("admin") && (
        <Card className="mb-6">
          <h2 className="font-semibold">{t("conn.connect")}</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {integrations?.map((integration) => (
              <Button
                key={integration.name}
                variant="secondary"
                disabled={!integration.available || action.busy}
                title={integration.available ? undefined : "Not configured on this server yet"}
                onClick={async () => {
                  if (integration.auth !== "oauth2") return setAdding(integration);
                  const name = window.prompt(`Name this ${integration.label} connection`, integration.name);
                  if (!name) return;
                  const result = await action.run(() =>
                    api<{ authorization_url: string }>(`${base}/connections/oauth/${integration.name}/start`, { body: { name } }),
                  );
                  if (result) window.location.href = result.authorization_url;
                }}
              >
                {integration.label}
              </Button>
            ))}
          </div>
          {adding && (
            <AddConnectionForm
              integration={adding}
              onDone={() => {
                setAdding(null);
                reload();
              }}
            />
          )}
        </Card>
      )}

      {loading && !connections ? (
        <Loading />
      ) : connections && connections.length === 0 ? (
        <EmptyState icon={Plug} title={t("conn.empty")}>Connect Airtable, your mailbox, Google Sheets or any API.</EmptyState>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {connections?.map((connection) => (
            <Card key={connection.id}>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="font-semibold">{connection.name}</h3>
                  <p className="text-xs text-slate-500">{connection.provider} · last used {formatTime(connection.last_used_at)}</p>
                </div>
                <StatusBadge status={connection.status} />
              </div>
              {connection.last_error && <p className="mt-2 text-sm text-orange-700">{connection.last_error}</p>}
              <ConnectionHealth
                connection={connection}
                integration={integrations?.find((item) => item.name === connection.provider)}
                onChanged={reload}
              />
              <dl className="mt-3 space-y-1 text-xs text-slate-600">
                {Object.entries({ ...connection.config, ...connection.secrets }).map(([key, value]) => (
                  <div key={key} className="flex gap-2">
                    <dt className="text-slate-400">{key}</dt>
                    <dd className="truncate">{String(value)}</dd>
                  </div>
                ))}
              </dl>
              <p className="mt-3 text-xs text-slate-500">
                Use in a step: <code>{`"connection": "${connection.name}"`}</code>
              </p>
              {can("admin") && (
                <Button
                  variant="ghost"
                  className="mt-2 px-0 text-red-600"
                  onClick={async () => {
                    if (!window.confirm(`Disconnect ${connection.name}? Its stored credentials are deleted.`)) return;
                    await action.run(() => api(`${base}/connections/${connection.id}`, { method: "DELETE" }));
                    reload();
                  }}
                >
                  {t("conn.disconnect")}
                </Button>
              )}
            </Card>
          ))}
        </div>
      )}
    </>
  );
}

function AddConnectionForm({ integration, onDone }: { integration: IntegrationInfo; onDone: () => void }) {
  const { base } = useSession();
  const { t } = useI18n();
  const action = useAction();
  const [name, setName] = useState(integration.name);
  const [values, setValues] = useState<Record<string, string>>({});

  const set = (key: string) => (event: React.ChangeEvent<HTMLInputElement>) =>
    setValues({ ...values, [key]: event.target.value });

  return (
    <form
      className="mt-4 grid gap-3 border-t border-slate-200 pt-4 md:grid-cols-2"
      onSubmit={async (event) => {
        event.preventDefault();
        const pick = (fields: string[]) =>
          Object.fromEntries(fields.filter((f) => values[f]).map((f) => [f, values[f]]));
        const done = await action.run(() =>
          api(`${base}/connections`, {
            body: {
              provider: integration.name,
              name,
              config: pick(integration.config_fields),
              secrets: pick(integration.secret_fields),
            },
          }),
        );
        if (done) onDone();
      }}
    >
      <Field label="Connection name" hint="Workflows refer to it by this name.">
        <input className={inputClass} value={name} onChange={(e) => setName(e.target.value)} required />
      </Field>
      {integration.config_fields.map((field) => (
        <Field key={field} label={field.replaceAll("_", " ")} hint={integration.required_config.includes(field) ? undefined : "Optional"}>
          <input
            className={inputClass}
            value={values[field] ?? ""}
            onChange={set(field)}
            required={integration.required_config.includes(field)}
          />
        </Field>
      ))}
      {integration.secret_fields.map((field) => (
        <Field key={field} label={field.replaceAll("_", " ")} hint="Encrypted; never shown again.">
          <input className={inputClass} type="password" autoComplete="off" value={values[field] ?? ""} onChange={set(field)} required />
        </Field>
      ))}
      <div className="md:col-span-2">
        <ErrorNote message={action.error} />
        <div className="mt-2 flex gap-2">
          <Button type="submit" disabled={action.busy}>{t("conn.save")}</Button>
          <Button type="button" variant="ghost" onClick={onDone}>{t("common.cancel")}</Button>
        </div>
      </div>
    </form>
  );
}

/** "Check connection" and, when broken, a one-click way to reconnect. */
function ConnectionHealth({
  connection,
  integration,
  onChanged,
}: {
  connection: Connection;
  integration?: IntegrationInfo;
  onChanged: () => void;
}) {
  const { base, can } = useSession();
  const { t } = useI18n();
  const action = useAction();
  const [result, setResult] = useState<{ ok: boolean | null; message: string } | null>(null);
  const [secrets, setSecrets] = useState<Record<string, string> | null>(null);

  async function check() {
    const outcome = await action.run(() =>
      api<{ ok: boolean | null; message: string }>(`${base}/connections/${connection.id}/check`, { body: {} }),
    );
    if (outcome) {
      setResult(outcome);
      onChanged();
    }
  }

  async function reconnect() {
    if (integration?.auth === "oauth2") {
      // Signing in again under the same name replaces the stored tokens
      const started = await action.run(() =>
        api<{ authorization_url: string }>(`${base}/connections/oauth/${connection.provider}/start`, {
          body: { name: connection.name },
        }),
      );
      if (started) window.location.href = started.authorization_url;
      return;
    }
    setSecrets(Object.fromEntries((integration?.secret_fields ?? []).map((field) => [field, ""])));
  }

  return (
    <div className="mt-3 space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        {can("member") && (
          <Button variant="secondary" className="px-2.5 py-1 text-xs" disabled={action.busy} onClick={check}>
            {action.busy ? t("conn.checking") : t("conn.check")}
          </Button>
        )}
        {can("admin") && connection.status === "error" && (
          <Button className="px-2.5 py-1 text-xs" disabled={action.busy} onClick={reconnect}>
            {t("conn.reconnect")}
          </Button>
        )}
        {connection.last_checked_at && (
          <span className="text-xs text-slate-500">{t("conn.lastChecked", { time: formatTime(connection.last_checked_at) })}</span>
        )}
      </div>
      {result && (
        <p
          role="status"
          className={`text-xs ${result.ok ? "text-emerald-700" : result.ok === null ? "text-slate-500" : "text-orange-700"}`}
        >
          {result.message}
        </p>
      )}
      <ErrorNote message={action.error} />
      {secrets && (
        <form
          className="space-y-2 rounded-lg bg-slate-50 p-3"
          onSubmit={async (event) => {
            event.preventDefault();
            const saved = await action.run(() =>
              api(`${base}/connections/${connection.id}/secrets`, { method: "PUT", body: { secrets } }),
            );
            if (saved !== undefined) {
              setSecrets(null);
              await check();
            }
          }}
        >
          <p className="text-xs text-slate-600">{t("conn.newSecrets")}</p>
          {Object.keys(secrets).map((field) => (
            <input
              key={field}
              className={inputClass}
              type="password"
              autoComplete="off"
              aria-label={field.replaceAll("_", " ")}
              placeholder={field.replaceAll("_", " ")}
              value={secrets[field]}
              onChange={(event) => setSecrets({ ...secrets, [field]: event.target.value })}
              required
            />
          ))}
          <div className="flex gap-2">
            <Button type="submit" className="px-2.5 py-1 text-xs" disabled={action.busy}>{t("common.save")}</Button>
            <Button type="button" variant="ghost" className="px-2.5 py-1 text-xs" onClick={() => setSecrets(null)}>
              {t("common.cancel")}
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
