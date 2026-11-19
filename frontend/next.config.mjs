// All algorithm work runs in the Python backend; Next.js proxies /api/* to it.
// Configure via .env.local (see .env.example).
const API_PROXY_TARGET = (
  process.env.API_PROXY_TARGET ||
  process.env.WM_API_URL ||
  "http://127.0.0.1:8000"
).replace(/\/+$/, "");

const PROXY_TIMEOUT_MS = Number(process.env.PROXY_TIMEOUT_MS || 300000);
const MAX_BODY_SIZE = process.env.MAX_BODY_SIZE || "120mb";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    proxyTimeout: Number.isFinite(PROXY_TIMEOUT_MS) ? PROXY_TIMEOUT_MS : 300000,
    middlewareClientMaxBodySize: MAX_BODY_SIZE,
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_PROXY_TARGET}/api/:path*` }];
  },
};

export default nextConfig;
