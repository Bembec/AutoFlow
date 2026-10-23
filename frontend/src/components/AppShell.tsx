"use client";

import {
  BarChart3,
  CheckCircle2,
  CreditCard,
  FileText,
  History,
  LayoutDashboard,
  LogOut,
  type LucideIcon,
  Menu,
  Plug,
  Settings,
  Workflow,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { Logo } from "@/components/Logo";
import { LANGUAGES, type Language, type MessageKey, useI18n } from "@/lib/i18n";
import { SessionProvider, useSession } from "@/lib/session";
import { useApi } from "@/lib/useApi";
import type { Dashboard } from "@/lib/types";

const NAV: { href: string; label: MessageKey; icon: LucideIcon }[] = [
  { href: "/dashboard", label: "nav.dashboard", icon: LayoutDashboard },
  { href: "/workflows", label: "nav.workflows", icon: Workflow },
  { href: "/executions", label: "nav.runs", icon: History },
  { href: "/insights", label: "nav.insights", icon: BarChart3 },
  { href: "/approvals", label: "nav.approvals", icon: CheckCircle2 },
  { href: "/invoices", label: "nav.invoices", icon: FileText },
  { href: "/connections", label: "nav.connections", icon: Plug },
  { href: "/billing", label: "nav.billing", icon: CreditCard },
  { href: "/settings", label: "nav.settings", icon: Settings },
];

const selectClass = "w-full rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-700";

function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { me, workspace, base, switchWorkspace, logout } = useSession();
  const [open, setOpen] = useState(false);
  const { data: dashboard } = useApi<Dashboard>(`${base}/dashboard`);
  const { t, language, setLanguage } = useI18n();

  const languagePicker = (
    <select
      aria-label={t("nav.language")}
      value={language}
      onChange={(event) => setLanguage(event.target.value as Language)}
      className={selectClass}
    >
      {Object.entries(LANGUAGES).map(([code, { label }]) => (
        <option key={code} value={code}>{label}</option>
      ))}
    </select>
  );

  const nav = (
    <nav aria-label={t("nav.menu")} className="flex flex-col gap-0.5">
      {NAV.map((item) => {
        const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={() => setOpen(false)}
            aria-current={active ? "page" : undefined}
            className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
              active ? "bg-brand-50 font-medium text-brand-700" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
            }`}
          >
            <Icon aria-hidden className={`size-4 shrink-0 ${active ? "text-brand-600" : "text-slate-400"}`} />
            <span className="flex-1">{t(item.label)}</span>
            {item.href === "/approvals" && dashboard && dashboard.pending_approvals > 0 && (
              <span className="rounded-full bg-amber-500 px-1.5 text-xs font-semibold text-white">
                {dashboard.pending_approvals}
              </span>
            )}
          </Link>
        );
      })}
    </nav>
  );

  return (
    <div className="min-h-screen lg:flex">
      <a
        href="#main"
        className="sr-only z-50 rounded-lg bg-white px-3 py-2 text-sm font-medium shadow focus:not-sr-only focus:fixed focus:left-4 focus:top-4"
      >
        {t("ui.skip")}
      </a>
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-slate-200 bg-white p-4 lg:flex">
        <Link href="/dashboard" className="mb-6 px-3 text-lg">
          <Logo />
        </Link>
        {nav}
        <div className="mt-auto space-y-2 border-t border-slate-200 pt-4">
          <WorkspaceSwitcher
            workspaces={me.workspaces}
            current={workspace.id}
            onChange={switchWorkspace}
          />
          {languagePicker}
          <p className="truncate px-1 text-xs text-slate-500">{me.email}</p>
          <button onClick={logout} className="inline-flex items-center gap-1.5 px-1 text-xs text-slate-500 hover:text-slate-900">
            <LogOut aria-hidden className="size-3.5" />
            {t("nav.signOut")}
          </button>
        </div>
      </aside>

      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 lg:hidden">
        <Link href="/dashboard">
          <Logo />
        </Link>
        {dashboard && dashboard.pending_approvals > 0 && (
          <Link href="/approvals" className="ml-auto mr-3 rounded-full bg-amber-500 px-3 py-1 text-sm font-semibold text-white">
            {t("nav.toApprove", { count: dashboard.pending_approvals })}
          </Link>
        )}
        <button
          onClick={() => setOpen(!open)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
          aria-expanded={open}
          aria-controls="mobile-menu"
        >
          {open ? <X aria-hidden className="size-4" /> : <Menu aria-hidden className="size-4" />}
          {t("nav.menu")}
        </button>
      </header>
      {open && (
        <div id="mobile-menu" className="border-b border-slate-200 bg-white p-4 lg:hidden">
          {nav}
          <div className="mt-4 space-y-2">
            <WorkspaceSwitcher workspaces={me.workspaces} current={workspace.id} onChange={switchWorkspace} />
            {languagePicker}
            <button onClick={logout} className="inline-flex items-center gap-1.5 text-sm text-slate-600">
              <LogOut aria-hidden className="size-4" />
              {t("nav.signOut")}
            </button>
          </div>
        </div>
      )}

      <main id="main" tabIndex={-1} className="mx-auto w-full min-w-0 max-w-7xl flex-1 px-4 py-6 outline-none sm:px-8">
        {dashboard?.automation_paused && (
          <div role="alert" className="mb-6 rounded-xl border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800">
            <strong>{t("banner.stopped")}</strong> {dashboard.paused_reason}{" "}
            <Link href="/settings" className="underline">{t("banner.resume")}</Link>
          </div>
        )}
        {children}
      </main>
    </div>
  );
}

function WorkspaceSwitcher({
  workspaces,
  current,
  onChange,
}: {
  workspaces: { id: number; name: string; role: string }[];
  current: number;
  onChange: (id: number) => void;
}) {
  return (
    <select
      aria-label="Workspace"
      value={current}
      onChange={(event) => onChange(Number(event.target.value))}
      className={selectClass}
    >
      {workspaces.map((workspace) => (
        <option key={workspace.id} value={workspace.id}>
          {workspace.name} ({workspace.role})
        </option>
      ))}
    </select>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <Shell>{children}</Shell>
    </SessionProvider>
  );
}
