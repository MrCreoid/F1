import type { NextConfig } from "next";

/**
 * The browser only ever talks to one origin. `/api/*` is rewritten to the FastAPI
 * service, so there is no CORS to configure and no hardcoded backend host in client
 * code — but the boundary is still a real one: two processes, two languages, HTTP
 * between them. Point WW_BACKEND at another host to split them across machines.
 */
const BACKEND = process.env.WW_BACKEND ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // Next dev blocks its own /_next/static chunks unless the host is listed here, which
  // silently 403s the client bundle when the app is opened on 127.0.0.1 rather than
  // localhost. Both are the same machine and both get used, so allow both.
  allowedDevOrigins: ["127.0.0.1", "localhost"],

  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND}/api/:path*` }];
  },
};

export default nextConfig;
