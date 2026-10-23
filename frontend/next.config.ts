import type { NextConfig } from "next";

// The browser talks to /api/*; Next.js forwards it to the AutoFlow API,
// so the app and the API share one origin (no CORS setup needed).
const apiUrl = process.env.AUTOFLOW_API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // Self-contained server for the Docker image (.next/standalone)
  output: "standalone",
  cacheComponents: true,
  partialPrefetching: true,
  experimental: {
    // Signed-in pages load per-user data in the browser by design, so only
    // pages that declare `instant` (the public pages) are validated for
    // instant navigation.
    instantInsights: { validationLevel: "manual-warning" },
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${apiUrl}/:path*` },
      // Public webhook URLs are served from the app's address too
      { source: "/hooks/:path*", destination: `${apiUrl}/hooks/:path*` },
      // The MCP server for outside AI assistants
      { source: "/mcp", destination: `${apiUrl}/mcp` },
      // Customers open invoice links on the app's address
      { source: "/invoices/:path*", destination: `${apiUrl}/invoices/:path*` },
    ];
  },
};

export default nextConfig;
