// All algorithm work runs in the Python backend; Next.js proxies /api/* to it.
const API = process.env.WM_API_URL || "http://127.0.0.1:8000";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: { proxyTimeout: 300000, middlewareClientMaxBodySize: "120mb" },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API}/api/:path*` }];
  },
};
export default nextConfig;
