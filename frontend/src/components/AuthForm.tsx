"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useSyncExternalStore } from "react";

import { Logo } from "@/components/Logo";
import { Button, ErrorNote, Field, inputClass } from "@/components/ui";
import { ApiError, api, getToken, setToken } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { peekPendingTask } from "@/lib/pendingTask";
import { useAction } from "@/lib/useApi";

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const { busy, error, run } = useAction();
  const { t } = useI18n();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [needsCode, setNeedsCode] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();

    const done = await run(async () => {
      if (mode === "register") {
        await api("/auth/register", { body: { name, email, password } });
      }
      let access_token: string;
      try {
        ({ access_token } = await api<{ access_token: string }>("/auth/login", {
          body: { email, password, ...(needsCode ? { code } : {}) },
        }));
      } catch (failure) {
        if (failure instanceof ApiError && failure.message === "two_factor_required") {
          setNeedsCode(true);
          return false;
        }
        throw failure;
      }
      setToken(access_token);
      return true;
    });

    // A task typed into the website demo goes straight to the AI builder
    if (done) router.push(mode === "login" ? "/dashboard" : peekPendingTask() ? "/workflows/new" : "/get-started");
  }

  const signedIn = useSyncExternalStore(() => () => {}, () => Boolean(getToken()), () => false);

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div>
          <Link href="/" className="text-lg">
            <Logo />
          </Link>
          {signedIn && (
            <p className="mt-4 rounded-lg bg-brand-50 px-3 py-2 text-sm text-brand-900">
              {t("auth.alreadyIn")}{" "}
              <Link href="/dashboard" className="font-medium underline">{t("auth.openApp")}</Link>
            </p>
          )}
          <h1 className="mt-4 text-xl font-semibold">
            {mode === "login" ? t("auth.signIn") : t("auth.createAccount")}
          </h1>
        </div>

        {mode === "register" && (
          <Field label={t("auth.name")}>
            <input className={inputClass} value={name} onChange={(e) => setName(e.target.value)} required />
          </Field>
        )}
        <Field label={t("auth.email")}>
          <input
            className={inputClass}
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </Field>
        <Field label={t("auth.password")} hint={mode === "register" ? t("auth.passwordHint") : undefined}>
          <input
            className={inputClass}
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            minLength={mode === "register" ? 8 : undefined}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </Field>

        {needsCode && (
          <Field label={t("auth.code")} hint={t("auth.codeHint")}>
            <input
              className={`${inputClass} tracking-widest`}
              inputMode="text"
              autoComplete="one-time-code"
              autoFocus
              value={code}
              onChange={(e) => setCode(e.target.value)}
              required
            />
          </Field>
        )}

        <ErrorNote message={error} />

        <Button type="submit" disabled={busy} className="w-full">
          {busy ? t("auth.wait") : mode === "login" ? t("auth.signIn") : t("auth.create")}
        </Button>

        <p className="text-center text-sm text-slate-500">
          {mode === "login" ? (
            <>
              {t("auth.newHere")} <Link href="/register" className="text-brand-600 hover:underline">{t("auth.create")}</Link>
            </>
          ) : (
            <>
              {t("auth.haveAccount")} <Link href="/login" className="text-brand-600 hover:underline">{t("auth.signIn")}</Link>
            </>
          )}
        </p>
      </form>
    </main>
  );
}
