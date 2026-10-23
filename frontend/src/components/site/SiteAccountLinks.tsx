"use client";

import Link from "next/link";
import { useSyncExternalStore } from "react";

import { getToken } from "@/lib/api";
import { useSiteText } from "@/lib/site-i18n";

// Signed in = a session token in this browser (checked again by the app itself)
const signedIn = () => Boolean(getToken());
const subscribe = (listener: () => void) => {
  window.addEventListener("storage", listener);
  return () => window.removeEventListener("storage", listener);
};

/** Header links: "Sign in / Start free", or "Open the app" for people already signed in. */
export function SiteAccountLinks({ variant = "header" }: { variant?: "header" | "menu" }) {
  const text = useSiteText();
  const isSignedIn = useSyncExternalStore(subscribe, signedIn, () => false);

  if (variant === "menu") {
    return isSignedIn ? (
      <Link href="/dashboard" className="block rounded-lg px-3 py-2 font-medium text-brand-700 hover:bg-slate-100">
        {text("Open the app")}
      </Link>
    ) : (
      <Link href="/login" className="block rounded-lg px-3 py-2 text-slate-700 hover:bg-slate-100">{text("Sign in")}</Link>
    );
  }

  if (isSignedIn) {
    return (
      <Link href="/dashboard" className="rounded-lg bg-brand-600 px-3 py-2 font-medium text-white hover:bg-brand-500">
        {text("Open the app")}
      </Link>
    );
  }
  return (
    <>
      <Link href="/login" className="hidden rounded-lg px-3 py-2 text-slate-700 hover:bg-slate-100 sm:block">
        {text("Sign in")}
      </Link>
      <Link href="/register" className="rounded-lg bg-brand-600 px-3 py-2 font-medium text-white hover:bg-brand-500">
        {text("Start free")}
      </Link>
    </>
  );
}

/** A big call to action: "Start free", or "Open the app" when signed in. */
export function StartOrOpen({ className }: { className: string }) {
  const text = useSiteText();
  const isSignedIn = useSyncExternalStore(subscribe, signedIn, () => false);
  return (
    <Link href={isSignedIn ? "/dashboard" : "/register"} className={className}>
      {text(isSignedIn ? "Open the app" : "Start free")}
    </Link>
  );
}
