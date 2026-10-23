import { Bot, Database, Globe, type LucideIcon, Mail, MessageSquare, ShoppingBag, Store, Table, Webhook } from "lucide-react";
import type { Metadata } from "next";

import { SiteCta, SiteHero } from "@/components/site/SiteChrome";

export const instant = true;

export const metadata: Metadata = { title: "Integrations" };

const GROUPS: { title: string; items: { icon: LucideIcon; name: string; text: string }[] }[] = [
  {
    title: "Your store",
    items: [
      { icon: ShoppingBag, name: "Shopify", text: "Paid orders, checkouts and more arrive as signed webhooks. Tag orders and add notes through the Admin API." },
      { icon: Store, name: "WooCommerce", text: "Order webhooks with WooCommerce signatures, plus order notes and status updates through the REST API." },
    ],
  },
  {
    title: "Email",
    items: [
      { icon: Mail, name: "Gmail and any email account", text: "Send from your own address, and start workflows when an email or invoice lands in a folder." },
    ],
  },
  {
    title: "Data and spreadsheets",
    items: [
      { icon: Table, name: "Google Sheets", text: "Add rows to your spreadsheets with secure Google sign-in." },
      { icon: Database, name: "Airtable", text: "Create and update records in your bases." },
    ],
  },
  {
    title: "Team and alerts",
    items: [
      { icon: MessageSquare, name: "Slack", text: "Get approval requests and failure alerts in a channel." },
    ],
  },
  {
    title: "Everything else",
    items: [
      { icon: Webhook, name: "Webhooks", text: "Any app that can send a signed webhook can start a workflow." },
      { icon: Globe, name: "Any REST API", text: "Call other services with stored, encrypted credentials." },
      { icon: Bot, name: "AI steps", text: "Read documents and PDFs, sort messages, summarise, translate and draft replies." },
    ],
  },
];

export default function IntegrationsPage() {
  return (
    <>
      <SiteHero eyebrow="Integrations" title="Connects to the tools you already use">
        <p>Credentials are encrypted and never shown again. Disconnect any app at any time.</p>
      </SiteHero>
      <div className="mx-auto max-w-6xl space-y-12 px-4 pb-20 sm:px-6">
        {GROUPS.map((group) => (
          <section key={group.title}>
            <h2 className="mb-4 text-xl font-semibold">{group.title}</h2>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {group.items.map(({ icon: Icon, name, text }) => (
                <div key={name} className="flex gap-4 rounded-2xl border border-slate-200 p-5">
                  <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                    <Icon aria-hidden className="size-5" />
                  </span>
                  <div>
                    <h3 className="font-semibold">{name}</h3>
                    <p className="mt-1 text-sm text-slate-600">{text}</p>
                  </div>
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
