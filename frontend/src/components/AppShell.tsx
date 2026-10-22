"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { SessionProvider, useSession } from "@/lib/session";
import { useApi } from "@/lib/useApi";
import type { Dashboard } from "@/lib/types";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/workflows", label: "Workflows" },
  { href: "/executions", label: "Run history" },
  { href: "/approvals", label: "Approvals" },
  { href: "/connections", label: "Connected apps" },
  { href: "/billing", label: "Plan & usage" },
  { href: "/settings", label: "Settings" },
];

function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { me, workspace, base, switchWorkspace, logout } = useSession();
  const [open, setOpen] = useState(false);
  const { data: dashboard } = useApi<Dashboard>(`${base}/dashboard`);

  const nav = (
    <nav className="flex flex-col gap-1">
      {NAV.map((item) => {
        const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={() => setOpen(false)}
            className={`flex items-center justify-between rounded-lg px-3 py-2 text-sm ${
              active ? "bg-indigo-50 font-medium text-indigo-700" : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            {item.label}
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
      <aside className="hidden w-60 shrink-0 flex-col border-r border-slate-200 bg-white p-4 lg:flex">
        <Link href="/dashboard" className="mb-6 px-3 text-lg font-semibold">
          Auto<span className="text-indigo-600">Flow</span>
        </Link>
        {nav}
        <div className="mt-auto space-y-2 border-t border-slate-200 pt-4">
          <WorkspaceSwitcher
            workspaces={me.workspaces}
            current={workspace.id}
            onChange={switchWorkspace}
          />
          <p className="truncate px-1 text-xs text-slate-500">{me.email}</p>
          <button onClick={logout} className="px-1 text-xs text-slate-500 hover:text-slate-900">
            Sign out
          </button>
        </div>
      </aside>

      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 lg:hidden">
        <Link href="/dashboard" className="font-semibold">
          Auto<span className="text-indigo-600">Flow</span>
        </Link>
        <button
          onClick={() => setOpen(!open)}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
          aria-expanded={open}
        >
          Menu
        </button>
      </header>
      {open && (
        <div className="border-b border-slate-200 bg-white p-4 lg:hidden">
          {nav}
          <div className="mt-4 space-y-2">
            <WorkspaceSwitcher workspaces={me.workspaces} current={workspace.id} onChange={switchWorkspace} />
            <button onClick={logout} className="text-sm text-slate-600">Sign out</button>
          </div>
        </div>
      )}

      <main className="min-w-0 flex-1 px-4 py-6 sm:px-8">
        {dashboard?.automation_paused && (
          <div role="alert" className="mb-6 rounded-xl border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800">
            <strong>All automations are stopped.</strong> {dashboard.paused_reason}{" "}
            <Link href="/settings" className="underline">Resume in Settings</Link>
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
      className="w-full rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm"
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
