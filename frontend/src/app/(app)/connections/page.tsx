"use client";

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
        <EmptyState title={t("conn.empty")}>Connect Airtable, your mailbox, Google Sheets or any API.</EmptyState>
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
