"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiError, api, setToken } from "@/lib/api";
import type { Me, WorkspaceWithRole } from "@/lib/types";

const WORKSPACE_KEY = "autoflow.workspace";

interface Session {
  me: Me;
  workspace: WorkspaceWithRole;
  /** `/workspaces/{id}` — prefix for workspace API paths */
  base: string;
  can: (role: "member" | "admin") => boolean;
  switchWorkspace: (id: number) => void;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

const SessionContext = createContext<Session | null>(null);

const RANK = { viewer: 0, member: 1, admin: 2, owner: 3 } as const;

function readWorkspaceId(): number | null {
  try {
    const value = window.localStorage.getItem(WORKSPACE_KEY);
    return value ? Number(value) : null;
  } catch {
    return null;
  }
}

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [workspaceId, setWorkspaceId] = useState<number | null>(null);

  const load = useCallback(async (): Promise<Me | null> => {
    try {
      return await api<Me>("/me");
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setToken(null);
        router.replace("/login");
        return null;
      }
      throw error;
    }
  }, [router]);

  const apply = useCallback((current: Me | null) => {
    if (!current) return;
    setMe(current);
    const stored = readWorkspaceId();
    const valid = current.workspaces.find((w) => w.id === stored) ?? current.workspaces[0];
    setWorkspaceId(valid?.id ?? null);
  }, []);

  const refresh = useCallback(async () => apply(await load()), [apply, load]);

  useEffect(() => {
    let cancelled = false;
    load().then((current) => !cancelled && apply(current));
    return () => {
      cancelled = true;
    };
  }, [apply, load]);

  const value = useMemo<Session | null>(() => {
    if (!me || workspaceId === null) return null;
    const workspace = me.workspaces.find((w) => w.id === workspaceId) ?? me.workspaces[0];

    return {
      me,
      workspace,
      base: `/workspaces/${workspace.id}`,
      can: (role) => RANK[workspace.role] >= RANK[role],
      switchWorkspace: (id) => {
        try {
          window.localStorage.setItem(WORKSPACE_KEY, String(id));
        } catch {
          // ignore: the choice just won't be remembered
        }
        setWorkspaceId(id);
        router.push("/dashboard");
      },
      refresh,
      logout: async () => {
        await api("/auth/logout", { method: "POST" }).catch(() => undefined);
        setToken(null);
        router.replace("/login");
      },
    };
  }, [me, workspaceId, refresh, router]);

  if (!value) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-slate-500">
        Loading your workspace…
      </div>
    );
  }

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): Session {
  const session = useContext(SessionContext);
  if (!session) throw new Error("useSession must be used inside SessionProvider");
  return session;
}
