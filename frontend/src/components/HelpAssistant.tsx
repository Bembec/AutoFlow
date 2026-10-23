"use client";

import { BookOpen, CircleHelp, X } from "lucide-react";
import { useState } from "react";

import { Button, ErrorNote, inputClass } from "@/components/ui";
import { api } from "@/lib/api";
import { useFeatures } from "@/lib/features";
import { useI18n } from "@/lib/i18n";
import { useSession } from "@/lib/session";
import { useAction } from "@/lib/useApi";

interface Source {
  article: string;
  section: string;
}

interface HelpAnswer {
  answer: string | null;
  sources: Source[];
  ai: boolean;
  found: boolean;
  excerpts?: (Source & { text: string })[];
}

/** Floating "Help" button and panel; answers come only from the help articles. */
export function HelpAssistant() {
  const { base } = useSession();
  const { t, language } = useI18n();
  const feature = useFeatures();
  const action = useAction();
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [reply, setReply] = useState<HelpAnswer | null>(null);

  if (!feature("help_assistant")) return null;

  async function ask(event: React.FormEvent) {
    event.preventDefault();
    if (question.trim().length < 3) return;
    const result = await action.run(() =>
      api<HelpAnswer>(`${base}/help/ask`, { body: { question: question.trim(), language } }),
    );
    if (result) setReply(result);
  }

  return (
    <>
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed right-4 bottom-4 z-40 inline-flex items-center gap-2 rounded-full bg-brand-600 px-4 py-2.5 text-sm font-medium text-white shadow-lg hover:bg-brand-500"
        >
          <CircleHelp aria-hidden className="size-4" />
          {t("help.button")}
        </button>
      )}
      {open && (
        <aside
          role="dialog"
          aria-label={t("help.title")}
          className="fixed right-4 bottom-4 z-40 flex max-h-[80vh] w-[min(26rem,calc(100vw-2rem))] flex-col rounded-2xl border border-slate-200 bg-white shadow-2xl"
        >
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <h2 className="flex items-center gap-2 font-semibold">
              <CircleHelp aria-hidden className="size-4 text-brand-600" />
              {t("help.title")}
            </h2>
            <button onClick={() => setOpen(false)} aria-label={t("help.close")} className="text-slate-400 hover:text-slate-800">
              <X aria-hidden className="size-4" />
            </button>
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3 text-sm">
            {reply && !reply.found && <p className="text-slate-700">{t("help.notFound")}</p>}
            {reply?.answer && <p className="whitespace-pre-line text-slate-800">{reply.answer}</p>}
            {reply && reply.found && !reply.ai && (
              <div className="space-y-3">
                <p className="text-slate-600">{t("help.noAi")}</p>
                {reply.excerpts?.map((excerpt) => (
                  <div key={`${excerpt.article}-${excerpt.section}`} className="rounded-lg bg-slate-50 p-3">
                    <p className="text-xs font-semibold text-slate-700">{excerpt.article} › {excerpt.section}</p>
                    <p className="mt-1 whitespace-pre-line text-xs text-slate-600">{excerpt.text}</p>
                  </div>
                ))}
              </div>
            )}
            {reply?.ai && reply.sources.length > 0 && (
              <div className="text-xs text-slate-500">
                <p className="font-medium">{t("help.sources")}</p>
                <ul className="mt-1 space-y-0.5">
                  {reply.sources.map((source) => (
                    <li key={`${source.article}-${source.section}`} className="flex items-center gap-1.5">
                      <BookOpen aria-hidden className="size-3" /> {source.article} › {source.section}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <ErrorNote message={action.error} />
          </div>

          <form onSubmit={ask} className="space-y-2 border-t border-slate-100 px-4 py-3">
            <textarea
              aria-label={t("help.title")}
              className={`${inputClass} min-h-16`}
              placeholder={t("help.placeholder")}
              maxLength={500}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  event.currentTarget.form?.requestSubmit();
                }
              }}
            />
            <div className="flex items-center justify-between gap-2">
              <p className="text-xs text-slate-400">{t("help.note")}</p>
              <Button type="submit" disabled={action.busy || question.trim().length < 3}>
                {action.busy ? t("help.asking") : t("help.ask")}
              </Button>
            </div>
          </form>
        </aside>
      )}
    </>
  );
}
