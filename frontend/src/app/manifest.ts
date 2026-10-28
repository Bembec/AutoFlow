import type { MetadataRoute } from "next";

import { BRAND } from "@/lib/brand";

// Lets owners add the app to their phone's home screen and open the
// approvals inbox like an app.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: BRAND.name,
    short_name: BRAND.name,
    description: "Approve and watch your business automations.",
    start_url: "/approvals",
    scope: "/",
    display: "standalone",
    background_color: "#0f1b3d",
    theme_color: BRAND.themeColor,
    icons: [
      { src: "/brand/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/brand/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/brand/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
    shortcuts: [
      { name: "Approvals", url: "/approvals" },
      { name: "Run history", url: "/executions" },
    ],
  };
}
