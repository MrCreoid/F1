import type { NextConfig } from "next";

/**
 * The browser only ever talks to one origin. `/api/*` is rewritten to the FastAPI
 * service, so there is no CORS to configure and no hardcoded backend host in client
 * code — but the boundary is still a real one: two processes, two languages, HTTP
 * between them. GitHub Pages has no Node server for rewrites, so its static build calls
 * the configured public API directly instead.
 */
const BACKEND = process.env.WW_BACKEND ?? "http://127.0.0.1:8000";
const IS_GITHUB_PAGES = process.env.GITHUB_PAGES === "true";

const nextConfig: NextConfig = {
  // Next dev blocks its own /_next/static chunks unless the host is listed here, which
  // silently 403s the client bundle when the app is opened on 127.0.0.1 rather than
  // localhost. Both are the same machine and both get used, so allow both.
  allowedDevOrigins: ["127.0.0.1", "localhost"],

  ...(IS_GITHUB_PAGES
    ? {
        output: "export",
        basePath: process.env.BASE_PATH,
        trailingSlash: true,
        // Keep a local `next dev` cache from colliding with a Pages export check.
        distDir: ".next-pages",
      }
    : {
        async rewrites() {
          return [
            { source: "/api/:path*", destination: `${BACKEND}/api/:path*` },
            // Per-frame thumbnails. Same reasoning as /api: the browser stays on one
            // origin, and `thumbnail_url` arrives from the backend as a path.
            { source: "/media/:path*", destination: `${BACKEND}/media/:path*` },
          ];
        },
      }),
};

export default nextConfig;
