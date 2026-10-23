// Product identity in one place. A rebrand changes this file, the brand
// colours in app/globals.css and the two icon.svg files.

export const BRAND = {
  name: "AutoFlow",
  /** The wordmark is drawn as `lead` + accent-coloured `accent` */
  lead: "Auto",
  accent: "Flow",
  tagline: "Tell it what you want done. AutoFlow builds the workflow, connects your apps, and runs it for you.",
  /** Must match --color-brand-600 in globals.css (used where CSS can't reach: browser chrome, manifest) */
  themeColor: "#4f46e5",
  supportEmail: "support@example.com",
} as const;
