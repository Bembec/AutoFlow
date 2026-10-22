import type { NextConfig } from "next";

// The browser talks to /api/*; Next.js forwards it to the AutoFlow API,
// so the app and the API share one origin (no CORS setup needed).
const apiUrl = process.env.AUTOFLOW_API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
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
    ];
  },
};

export default nextConfig;
