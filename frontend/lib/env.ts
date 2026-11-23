function parseNumber(raw: string | undefined, fallback: number): number {
  if (!raw) return fallback;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export const env = {
  /** Base URL for direct API calls (empty = use Next.js /api/* proxy rewrite). */
  apiUrl: (process.env.NEXT_PUBLIC_API_URL ?? "").trim().replace(/\/+$/, ""),
  /** App title in browser tab and page header. */
  appTitle: (process.env.NEXT_PUBLIC_APP_TITLE ?? "").trim() || "DCT Watermarking Lab",
  /** Default watermark settings in UI. */
  defaultAlpha: parseNumber(process.env.NEXT_PUBLIC_DEFAULT_ALPHA, 25),
  defaultSecretKey: (process.env.NEXT_PUBLIC_DEFAULT_SECRET_KEY ?? "").trim() || "my-secret-key",
  defaultMethod: (process.env.NEXT_PUBLIC_DEFAULT_METHOD === "lsb" ? "lsb" : "dct") as "dct" | "lsb",
  /** Client-side request timeout in milliseconds (default: 3 minutes). */
  requestTimeoutMs: parseNumber(process.env.NEXT_PUBLIC_REQUEST_TIMEOUT_MS, 180_000),
} as const;
