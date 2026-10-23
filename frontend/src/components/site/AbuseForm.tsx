"use client";

import { CheckCircle2 } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { Button, ErrorNote, Field, inputClass } from "@/components/ui";
import { api } from "@/lib/api";
import { useAction } from "@/lib/useApi";

const CATEGORIES = [
  { value: "phishing", label: "Phishing (asks for passwords, codes or payment)" },
  { value: "spam", label: "Spam (unwanted marketing or bulk email)" },
  { value: "other", label: "Something else" },
];

export function AbuseForm() {
  // Emails sent through AutoFlow link here with ?workspace=<id>
  const linked = useSearchParams().get("workspace") ?? "";
  const [category, setCategory] = useState("phishing");
  const [message, setMessage] = useState("");
  const [email, setEmail] = useState("");
  const [workspace, setWorkspace] = useState(linked);
  const [sent, setSent] = useState(false);
  const action = useAction();

  if (sent) {
    return (
      <div role="status" className="flex items-start gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 p-6 text-emerald-900">
        <CheckCircle2 aria-hidden className="mt-0.5 size-5 shrink-0" />
        <p>Thank you. Our team reviews every report and can stop a workspace from sending while we look into it.</p>
      </div>
    );
  }

  return (
    <form
      className="space-y-4 rounded-2xl border border-slate-200 p-6"
      onSubmit={async (event) => {
        event.preventDefault();
        const done = await action.run(() =>
          api("/abuse-reports", {
            body: {
              category,
              message,
              reporter_email: email.trim() || null,
              workspace_id: /^\d+$/.test(workspace.trim()) ? Number(workspace.trim()) : null,
            },
          }),
        );
        if (done !== undefined) setSent(true);
      }}
    >
      <Field label="What happened?">
        <select className={inputClass} value={category} onChange={(event) => setCategory(event.target.value)}>
          {CATEGORIES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
        </select>
      </Field>
      <Field label="Details" hint="Paste the message or describe it. Include the sender address and date if you can.">
        <textarea
          className={`${inputClass} min-h-32`}
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          minLength={10}
          maxLength={5000}
          required
        />
      </Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Your email (optional)" hint="Only used if we need to ask you something.">
          <input className={inputClass} type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
        </Field>
        <Field label="Workspace number (optional)" hint="From the email's X-AutoFlow-Workspace header.">
          <input className={inputClass} inputMode="numeric" value={workspace} onChange={(event) => setWorkspace(event.target.value)} />
        </Field>
      </div>
      <ErrorNote message={action.error} />
      <Button type="submit" disabled={action.busy}>{action.busy ? "Sending…" : "Send report"}</Button>
    </form>
  );
}
