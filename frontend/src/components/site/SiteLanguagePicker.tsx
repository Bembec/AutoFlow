"use client";

import { Globe } from "lucide-react";

import { LANGUAGES, type Language, useI18n } from "@/lib/i18n";
import { useSiteText } from "@/lib/site-i18n";

/** Language choice for the website; the app uses the same saved choice. */
export function SiteLanguagePicker() {
  const { language, setLanguage } = useI18n();
  const text = useSiteText();

  return (
    <label className="relative hidden items-center gap-1 rounded-lg px-2 py-2 text-slate-600 hover:bg-slate-100 sm:flex">
      <Globe aria-hidden className="size-4" />
      <span className="sr-only">{text("Language")}</span>
      <select
        value={language}
        onChange={(event) => setLanguage(event.target.value as Language)}
        className="cursor-pointer appearance-none bg-transparent pr-1 text-sm outline-none"
      >
        {Object.entries(LANGUAGES).map(([code, { label }]) => (
          <option key={code} value={code}>{label}</option>
        ))}
      </select>
    </label>
  );
}
