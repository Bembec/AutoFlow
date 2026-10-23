import {
  Bot,
  Download,
  Fingerprint,
  KeyRound,
  Lock,
  type LucideIcon,
  RefreshCw,
  ScrollText,
  ShieldCheck,
  Siren,
  Users,
  Webhook,
} from "lucide-react";
import type { Metadata } from "next";

import { SiteCta, SiteHero } from "@/components/site/SiteChrome";

export const instant = true;

export const metadata: Metadata = { title: "Security" };

// Only describe what the product actually does today. No certifications are
// claimed until they exist (hosting and legal pages are still to come).
const SECTIONS: { title: string; items: { icon: LucideIcon; title: string; text: string }[] }[] = [
  {
    title: "Your data stays yours",
    items: [
      {
        icon: Lock,
        title: "Separate workspaces",
        text: "Every business gets its own workspace. Each request is checked against it, so one shop can never see another's data.",
      },
      {
        icon: KeyRound,
        title: "Encrypted credentials",
        text: "Passwords and tokens for your apps are encrypted before they are stored and are never shown again, not even to you.",
      },
      {
        icon: Download,
        title: "Export or delete at any time",
        text: "Download everything in your workspace, or delete the workspace and your account yourself, from Settings.",
      },
    ],
  },
  {
    title: "You stay in control",
    items: [
      {
        icon: ShieldCheck,
        title: "Approvals for what matters",
        text: "Emails to customers wait for a person to approve them. You can require approval for every outside action.",
      },
      {
        icon: Siren,
        title: "Emergency stop and limits",
        text: "One switch pauses every automation. Daily limits on runs, emails and AI use prevent runaway costs.",
      },
      {
        icon: Bot,
        title: "Careful AI",
        text: "AI steps can only do what the workflow allows. Messages that look like manipulation attempts, and unsure answers, go to a person for review.",
      },
    ],
  },
  {
    title: "Secure accounts and connections",
    items: [
      {
        icon: Fingerprint,
        title: "Two-factor login",
        text: "Protect sign-in with any authenticator app, with one-time recovery codes. Passwords are stored only as salted scrypt hashes.",
      },
      {
        icon: Users,
        title: "Roles and an activity log",
        text: "Give teammates owner, admin, member or viewer access. Sign-ins, permission changes, publishes and approvals are logged.",
      },
      {
        icon: Webhook,
        title: "Signed webhooks",
        text: "Incoming store events are checked against a shared secret (including Shopify and WooCommerce signatures) before anything runs.",
      },
    ],
  },
  {
    title: "Dependable by design",
    items: [
      {
        icon: RefreshCw,
        title: "No double actions",
        text: "Retries are automatic but never repeat a step that may already have happened. Those runs are flagged for you to check.",
      },
      {
        icon: ScrollText,
        title: "A record of every run",
        text: "Each run keeps what it received, what every step did, and why anything failed.",
      },
      {
        icon: Lock,
        title: "Safe outbound calls",
        text: "Workflows can't be pointed at internal network addresses, which blocks a common class of attacks.",
      },
    ],
  },
];

export default function SecurityPage() {
  return (
    <>
      <SiteHero eyebrow="Security" title="Built to be trusted with your store">
        <p>Automation touches your customers and your money. Here is how we keep both safe.</p>
      </SiteHero>
      <div className="mx-auto max-w-6xl space-y-14 px-4 pb-20 sm:px-6">
        {SECTIONS.map((section) => (
          <section key={section.title}>
            <h2 className="mb-5 text-xl font-semibold">{section.title}</h2>
            <div className="grid gap-4 md:grid-cols-3">
              {section.items.map(({ icon: Icon, title, text }) => (
                <div key={title} className="rounded-2xl border border-slate-200 p-6">
                  <span className="flex size-10 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600">
                    <Icon aria-hidden className="size-5" />
                  </span>
                  <h3 className="mt-4 font-semibold">{title}</h3>
                  <p className="mt-2 text-sm text-slate-600">{text}</p>
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>
      <SiteCta />
    </>
  );
}
