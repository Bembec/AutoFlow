# Luphina brand guide

The product built in this repository is called **Luphina** (spelled exactly L-u-p-h-i-n-a). It was developed under the working name AutoFlow, which is still used for internal names (see *What keeps the old name*). The owner's brand brief is version 1.0, dated 28 October 2026, and is kept privately.

## Message hierarchy

1. **What it does:** practical, AI-powered business automation, including connected workflows, customer and message handling, and productivity.
2. **How it behaves:** dependable, understandable, controlled and human-centred. Trust is shown through the product itself: approvals, plain-language run history and an emergency stop.
3. **Why it's called Luphina:** a tribute to the founder's mother. This is a quiet founder story on the About page, never the sales pitch.

## Approved wording

| Use | Text |
| --- | --- |
| Philosophy / tagline | Turning Challenges Into Progress. |
| Home headline | Automate the busywork. Focus on what matters. |
| Home subheading | Luphina brings customer interactions, everyday tasks, and connected tools into simpler, smarter workflows. |
| Short description | AI-powered business automation for people and teams who want to work smarter. |
| One-liner | Luphina helps businesses simplify repetitive work, connect their tools, and turn everyday processes into intelligent workflows. |
| About bridge | Built to make progress easier. |
| Founder story | On `/about#our-story` (the draft from the brief, unchanged) |

**Never claim:**
- "zero errors", "100% uptime" or "fully secure";
- certifications, customer counts or testimonials that don't exist;
- a Latin or wolf origin for the name.

**There is no wolf in the identity.**

## Logo

- **The mark** is the approved ribbon symbol, used exactly as supplied. It is never redrawn, recoloured, stretched, mirrored or rotated.
- **Files** are in `frontend/public/brand/`:
  - `luphina-logo-original.png` / `.svg`: the files as supplied (138×177). The SVG wraps the same PNG; it is not a vector.
  - `luphina-mark.png`: the same image with only the screenshot edges removed (a 12-pixel white band at the top and a 1-pixel grey line at the bottom).
  - `icon-192.png`, `icon-512.png`, `icon-maskable-512.png`, plus `frontend/src/app/icon.png` (browser tab) and `apple-icon.png` (iPhone home screen): the mark centred on a Midnight square. Nothing about the mark itself is changed.
- **Still needed:** a clean, transparent master (ideally a true SVG) at high resolution. Today's image includes its mountain background and is small, so it softens when enlarged (for example the 512-pixel app icon). Monochrome and light/dark variants wait for that master.

## Colours

The tokens are in `frontend/src/app/globals.css` and are used as Tailwind classes (`bg-midnight`, `text-ink`…).

| Token | Hex | Use |
| --- | --- | --- |
| Midnight | `#0F1B3D` | Closing banners, app icon background, browser theme colour |
| Luphina Purple | `#6B5BFF` | `brand-500`; the accent scale `brand-50`…`brand-950` is built around it |
| Button purple | `#5A46F0` | `brand-600`: buttons and links, a little darker so white text stays readable |
| Sunrise Gold | `#F2C572` | Sparing highlights, such as the button on the closing banner. Never small text on white |
| Soft Lilac | `#EDEBFF` | Soft surfaces (home hero, Our story section) |
| Ivory | `#FAF8F4` | Page background |
| Ink | `#17213B` | Headlines and main text |

Success, warning and error colours stay green, amber and red, separate from the brand colours.

## Type

- **Inter:** the app, forms, tables and body text.
- **Lora (serif):** selected marketing headlines (`font-display`) and the philosophy line.
- **No script fonts** in the product.

## Where the brand lives in code

| What | Where |
| --- | --- |
| Name, philosophy, short description, mark path, theme colour, support email | `frontend/src/lib/brand.ts` |
| Colours and fonts | `frontend/src/app/globals.css`, `frontend/src/app/layout.tsx` |
| Logo component (header, sign-in, app sidebar) | `frontend/src/components/Logo.tsx` |
| Installed-app icons | `frontend/src/app/manifest.ts` |
| Product name in translated text | `frontend/src/lib/i18n.tsx`, `frontend/src/lib/site-i18n.tsx` (5 languages) |
| Help articles | `docs/help/*.md` (then `python backend/scripts/sync_help.py`) |
| Name in emails, notifications, authenticator apps, the AI prompts and the MCP server | `backend/src/autoflow/` (`notifications.py`, `accounts/two_factor.py`, `ai/builder.py`, `help_assistant.py`, `api/routes/mcp_server.py`) |

## What keeps the old name, on purpose

Renaming these would break existing installs, integrations or deployments, and the brief asks for approval first:
- the Python package `autoflow`;
- `AUTOFLOW_*` environment settings;
- the `X-AutoFlow-Signature`, `X-AutoFlow-Timestamp` and `X-AutoFlow-Workspace` headers that webhook senders and email filters rely on;
- database and Docker names;
- the GitHub repository name;
- browser storage keys.

A later, planned migration can rename them with a transition period.

## Open brand items

- **Trademark and name clearance:** not done. Nothing here is legal clearance.
- **Domain:** not chosen.
- **Final transparent vector logo:** needed (see *Logo*).
- **Official support email:** `luphina2026@gmail.com` is in use for now.
