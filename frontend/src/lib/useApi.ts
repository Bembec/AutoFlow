"use client";

import { useCallback, useEffect, useState } from "react";

import { api, errorMessage } from "@/lib/api";

interface Loaded<T> {
  key: string;
  data: T | null;
  error: string | null;
}

/** Load an API path; `reload()` fetches it again. Pass null to skip. */
export function useApi<T>(path: string | null) {
  const [version, setVersion] = useState(0);
  const [loaded, setLoaded] = useState<Loaded<T>>({ key: "", data: null, error: null });
  const key = `${path}#${version}`;

  useEffect(() => {
    if (path === null) return;
    let cancelled = false;

    api<T>(path).then(
      (data) => !cancelled && setLoaded({ key, data, error: null }),
      (failure) => !cancelled && setLoaded((previous) => ({ key, data: previous.data, error: errorMessage(failure) })),
    );

    // Ignore a slow response that arrives after the path changed
    return () => {
      cancelled = true;
    };
  }, [path, key]);

  const reload = useCallback(() => setVersion((current) => current + 1), []);
  const setData = useCallback((data: T) => setLoaded((previous) => ({ ...previous, data })), []);

  return {
    data: loaded.data,
    error: loaded.error,
    loading: path !== null && loaded.key !== key,
    reload,
    setData,
  };
}

/** Run an API action, tracking busy state and the last error. */
export function useAction() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async <T,>(action: () => Promise<T>): Promise<T | undefined> => {
    setBusy(true);
    setError(null);
    try {
      return await action();
    } catch (failure) {
      setError(errorMessage(failure));
      return undefined;
    } finally {
      setBusy(false);
    }
  }, []);

  return { busy, error, run, setError };
}
