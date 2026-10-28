# Decisions needed

These are the choices only you can make. The product is built so that each one is quick to apply once you decide. Each row says what it unblocks and where it goes in the code.

**Last updated:** 2026-10-28 (V49). Tick the box once you've decided, and tell Claude the answer.

## Most urgent (they block the launch)

| ☐ | Decision | Options | Recommendation in the roadmap | What it unblocks | Where it goes |
| --- | --- | --- | --- | --- | --- |
| ☑ | **Brand name and look** | Decided 2026-10-28: **Luphina**, with the ribbon logo, palette and wording from the brand brief | Done in V49 | | `docs/brand/README.md` |
| ☐ | **Brand follow-ups** | Trademark and name check; a domain; a clean transparent (vector) master of the logo | A trademark lawyer checks the name before you buy the domain; ask the designer for the logo as SVG with a transparent background | Final icons and monochrome logo versions; your own email address | `frontend/public/brand/`, `docs/brand/README.md` |
| ☐ | **Support email address** | `luphina2026@gmail.com` is used for now | Switch to an address on your domain once you have one | The "contact support" messages and the About page | `frontend/src/lib/brand.ts` → `supportEmail` |
| ☐ | **Hosting** | AWS, Google Cloud, or a simpler platform | Choose one region close to your first customers | Going live; a staging copy; backups and restore targets; status page; uptime monitoring; on-call; most of the real-world tests | `docs/operations.md` (deploy steps are ready: Docker images, CI, PostgreSQL) |
| ☐ | **Launch country and currency** | Where you live, US, UK, EU, Turkey, Africa… | One country first. Turkey-first is a credible option if the 20 owner interviews confirm it | Payments, data laws (GDPR, KVKK…), local integrations, prices, website wording | Kept country-neutral on purpose until you decide |
| ☐ | **Legal pages** | A startup lawyer, or a template service | Have a lawyer review them | Terms of service, privacy policy, acceptable-use policy (the product already enforces it), data processing agreement, list of sub-processors, AI-label wording for customer emails | New website pages (the structure is ready) |

## Product choices

| ☐ | Decision | Options | Recommendation | What it unblocks |
| --- | --- | --- | --- | --- |
| ☐ | **Positioning: what you lead with** | Deep focus on one niche; a reliability guarantee; done-for-you setup; a local market | Pick one. Plain-language building is now standard across competitors, so keep it as the entry point, not the headline | Final website copy, sales message |
| ☐ | **Shopify route** | A Shopify App Store app (billing through Shopify), or an independent platform (today's build) | Decide early: it changes billing, app review and sign-up | Shopify app review, Shopify billing |
| ☐ | **Gmail access** | Pay for Google's security assessment (CASA) to use Gmail sign-in; narrower scopes; or keep today's mailbox connection (IMAP/SMTP app password) | Today's build avoids the restricted Gmail scopes | A one-click "Sign in with Gmail" |
| ☐ | **Free plan** | Keep it; limit its AI use; or replace it with a trial | Decide with real cost numbers from the pilots | Final pricing page and plan limits |
| ☐ | **Plan prices and AI budgets** | Today's proposals: Free $0, Starter $29, Growth $99, Business $299, Enterprise custom; AI budgets $2 / $15 / $50 / $150 / unlimited | Test with the first paying customers | `backend/src/autoflow/billing/plans.json`, no code change needed |
| ☐ | **AI credit packs** | Price and size of extra AI credit packs | After you know real AI costs | A "buy more AI" option |
| ☐ | **AI providers and their data terms** | Which AI companies to use (today: Gemini first, Claude as fallback) and their no-training, retention and region terms | Choose providers that don't train on your customers' data, and publish the terms | The trust page, sub-processor list, `AUTOFLOW_AI_COST_PER_CALL_USD` |
| ☐ | **Feature defaults** | Everything is on by default since V48 | Keep, or switch some off until pilots go well | `AUTOFLOW_FEATURES` setting, no code change |

## Company and growth

| ☐ | Decision | Options | Recommendation | What it unblocks |
| --- | --- | --- | --- | --- |
| ☐ | **Who builds it next** | Founder plus AI help; hired engineers; a technical co-founder; an agency | A technical co-founder or first engineer who owns the code | The hiring plan; who owns each roadmap item (the status file has room for owners) |
| ☐ | **Build or buy integrations** | Build every connector; use a unified-API or embedded-integration service; build on an open-source engine | Buy or reuse for breadth, and build your own for the core apps | Outlook, Notion, HubSpot, QuickBooks, WhatsApp, Calendly and the "150+ integrations" goal |
| ☐ | **Funding route** | Bootstrap and grants; pre-seed; an accelerator | Bootstrap to paid pilots, then raise a pre-seed with proof | Team size, the compliance budget (SOC 2, penetration tests) |
| ☐ | **Second niche** (later) | Agencies, clinics, real estate, accounting… | After e-commerce works | Industry template packs beyond e-commerce |

## Things only you can do (not decisions, but needed)

- Talk to the **20 business owners** in your niche and sign the first **10 design partners**. They provide the real requests for the AI test set (today's 60 are made up) and the first case studies.
- Run the **real-world checks** in `docs/deferred-checks.md`: phone install, real Shopify or WooCommerce store, real Gmail, an AI key, a real MCP client, and a native-speaker review of the translations.
- Register the company, then set up accounts with the cloud provider, AI providers and Stripe.
