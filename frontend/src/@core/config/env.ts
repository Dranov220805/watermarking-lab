import type { WatermarkMethod } from "@/src/services/watermark-service/operations/models/input.model";

function parseNumber(raw: string | undefined, fallback: number): number {
  if (!raw) return fallback;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function parseMethod(raw: string | undefined): WatermarkMethod {
  return raw === "lsb" ? "lsb" : "dct";
}

function normalizePath(raw: string | undefined, fallback: string): string {
  const val = (raw ?? "").trim();
  if (!val) return fallback;
  return "/" + val.replace(/^\/+|\/+$/g, "");
}

export const env = {
  /** Base URL for direct API calls (empty string = use Next.js /api/* proxy rewrite). */
  apiUrl: (process.env.NEXT_PUBLIC_API_URL ?? "").trim().replace(/\/+$/, ""),
  /** Versioned API prefix (default: /api/v1). */
  apiPrefix: normalizePath(process.env.NEXT_PUBLIC_API_PREFIX, "/api/v1"),
  /** Display title in browser tab and page header. */
  appTitle: (process.env.NEXT_PUBLIC_APP_TITLE ?? "").trim() || "DCT Watermarking Lab",
  /** Default watermark settings in UI. */
  defaultAlpha: parseNumber(process.env.NEXT_PUBLIC_DEFAULT_ALPHA, 25),
  defaultSecretKey: (process.env.NEXT_PUBLIC_DEFAULT_SECRET_KEY ?? "").trim() || "my-secret-key",
  defaultMethod: parseMethod(process.env.NEXT_PUBLIC_DEFAULT_METHOD),
  /** Client-side HTTP request timeout in milliseconds (default: 3 minutes). */
  requestTimeoutMs: parseNumber(process.env.NEXT_PUBLIC_REQUEST_TIMEOUT_MS, 180_000),
} as const;
