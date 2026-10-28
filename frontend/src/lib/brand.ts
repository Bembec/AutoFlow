// Product identity in one place. A rebrand changes this file, the brand
// colours in app/globals.css and the images in public/brand/ (plus
// app/icon.png and app/apple-icon.png). The product name also appears in
// translated text (lib/i18n.tsx, lib/site-i18n.tsx) and the help articles.
// Internal names (the `autoflow` package, AUTOFLOW_* settings, X-AutoFlow-*
// headers) keep the original project name so integrations don't break.

export const BRAND = {
  name: "Luphina",
  /** Brand line from the Luphina brand brief */
  philosophy: "Turning Challenges Into Progress.",
  tagline: "AI-powered business automation for people and teams who want to work smarter.",
  /** The approved ribbon mark, as supplied (a raster; a transparent vector master is still to come) */
  mark: "/brand/luphina-mark.png",
  /** Browser chrome and installed-app colour: Midnight */
  themeColor: "#0f1b3d",
  supportEmail: "luphina2026@gmail.com",
} as const;
