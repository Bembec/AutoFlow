import type { MetadataRoute } from "next";

// Lets owners add AutoFlow to their phone's home screen and open the
// approvals inbox like an app.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "AutoFlow",
    short_name: "AutoFlow",
    description: "Approve and watch your business automations.",
    start_url: "/approvals",
    scope: "/",
    display: "standalone",
    background_color: "#f8fafc",
    theme_color: "#4f46e5",
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
