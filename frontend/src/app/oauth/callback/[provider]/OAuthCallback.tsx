"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { api, errorMessage } from "@/lib/api";

export function OAuthCallback() {
  const { provider } = useParams<{ provider: string }>();
  const searchParams = useSearchParams();
  const [message, setMessage] = useState("Finishing sign-in…");
  const [ok, setOk] = useState<boolean | null>(null);
  const started = useRef(false);

  useEffect(() => {
    // The code can only be exchanged once, so never send it twice
    if (started.current) return;
    started.current = true;

    api<{ connection: string }>(`/oauth/callback/${provider}?${searchParams.toString()}`)
      .then((result) => {
        setOk(true);
        setMessage(`Connected “${result.connection}”.`);
      })
      .catch((error) => {
        setOk(false);
        setMessage(errorMessage(error));
      });
  }, [provider, searchParams]);

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="max-w-sm rounded-xl border border-slate-200 bg-white p-6 text-center shadow-sm">
        <p className={ok === false ? "text-red-700" : "text-slate-800"}>{message}</p>
        {ok !== null && (
          <Link href="/connections" className="mt-4 inline-block text-sm text-indigo-600 hover:underline">
            Back to connected apps
          </Link>
        )}
      </div>
    </main>
  );
}
