import type { MetadataRoute } from "next";

import { BRAND } from "@/lib/brand";

// Lets owners add AutoFlow to their phone's home screen and open the
// approvals inbox like an app.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: BRAND.name,
    short_name: BRAND.name,
    description: "Approve and watch your business automations.",
    start_url: "/approvals",
    scope: "/",
    display: "standalone",
    background_color: "#f8fafc",
    theme_color: BRAND.themeColor,
    icons: [
      { src: "/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" },
      { src: "/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "maskable" },
    ],
    shortcuts: [
      { name: "Approvals", url: "/approvals" },
      { name: "Run history", url: "/executions" },
    ],
  };
}
