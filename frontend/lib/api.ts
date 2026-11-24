import { env } from "@/lib/env";

export interface ImgInfo { id: string; name: string; width: number; height: number; format: string; bytes: number; blocks: number; copies: number }
export type Method = "dct" | "lsb";
export type Mode = "search" | "aligned";
export interface LogoSpec { source: "standard" | "upload" | "text"; text: string; threshold: number; invert: boolean; file: File | null }
export const STANDARD_LOGO: LogoSpec = { source: "standard", text: "", threshold: 128, invert: false, file: null };

export interface EmbedOut extends ImgInfo { psnr: number | null; ssim: number | null; seconds: number }
export interface AttackOut extends ImgInfo { desc: string; psnr: number | null }
export interface ExtractOut {
  mode: Mode; blocks: number; copies: number; structure: number; structure_baseline: number; logo_png: string; seconds: number;
  nc?: number; ber?: number; score?: number; threshold?: number; null_mean?: number; null_max?: number; detected?: boolean;
  offset?: [number, number]; phase?: [number, number];
}

const apiUrl = (path: string) => `${env.apiUrl}${path}`;

async function fetchWithTimeout(url: string, init?: RequestInit): Promise<Response> {
  const timeoutMs = env.requestTimeoutMs;
  if (!timeoutMs || timeoutMs <= 0) return fetch(url, init);
  const controller = new AbortController();
  const ext = init?.signal;
  const onAbort = () => controller.abort();
  if (ext) {
    if (ext.aborted) controller.abort();
    else ext.addEventListener("abort", onAbort, { once: true });
  }
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } catch (err) {
    if (timedOut) throw new Error(`Request timed out after ${Math.round(timeoutMs / 1000)}s.`);
    throw err;
  } finally {
    clearTimeout(timer);
    if (ext) ext.removeEventListener("abort", onAbort);
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try { res = await fetchWithTimeout(apiUrl(path), init); } catch (err) {
    if ((err as Error)?.name === "AbortError" || (err instanceof Error && err.message.startsWith("Request timed out"))) throw err;
    throw new Error("Cannot reach the Python backend. Start it with `npm run api` (or check .env.local).");
  }
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`;
    try {
      const j = await res.json();
      msg = typeof j.detail === "string" ? j.detail : Array.isArray(j.detail) ? j.detail.map((d: { msg: string }) => d.msg).join("; ") : msg;
    } catch { /* keep default */ }
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
}

function logoFields(fd: FormData, l: LogoSpec) {
  fd.append("logo_source", l.source);
  fd.append("logo_text", l.text);
  fd.append("logo_threshold", String(l.threshold));
  fd.append("logo_invert", String(l.invert));
  if (l.source === "upload" && l.file) fd.append("logo_file", l.file);
}

export function upload(file: File): Promise<ImgInfo> {
  const fd = new FormData(); fd.append("file", file);
  return call<ImgInfo>("/api/upload", { method: "POST", body: fd });
}

export function embed(p: { imageId: string; key: string; alpha: number; method: Method; logo: LogoSpec }): Promise<EmbedOut> {
  const fd = new FormData();
  fd.append("image_id", p.imageId); fd.append("key", p.key); fd.append("alpha", String(p.alpha)); fd.append("method", p.method);
  logoFields(fd, p.logo);
  return call<EmbedOut>("/api/embed", { method: "POST", body: fd });
}

export function attack(p: { imageId: string; crop?: { x: number; y: number; w: number; h: number } | null; overwrite?: boolean; overwriteAlpha?: number; noise: number; jpeg: number }): Promise<AttackOut> {
  const fd = new FormData();
  fd.append("image_id", p.imageId);
  if (p.crop) { fd.append("crop_x", String(p.crop.x)); fd.append("crop_y", String(p.crop.y)); fd.append("crop_w", String(p.crop.w)); fd.append("crop_h", String(p.crop.h)); }
  if (p.overwrite) { fd.append("overwrite", "true"); if (p.overwriteAlpha != null) fd.append("overwrite_alpha", String(p.overwriteAlpha)); }
  fd.append("noise_sigma", String(p.noise)); fd.append("jpeg_quality", String(p.jpeg));
  return call<AttackOut>("/api/attack", { method: "POST", body: fd });
}

export function extract(p: { imageId: string; key: string; alpha: number; method: Method; mode: Mode; logo: LogoSpec }): Promise<ExtractOut> {
  const fd = new FormData();
  fd.append("image_id", p.imageId); fd.append("key", p.key); fd.append("alpha", String(p.alpha)); fd.append("method", p.method); fd.append("mode", p.mode);
  logoFields(fd, p.logo);
  return call<ExtractOut>("/api/extract", { method: "POST", body: fd });
}

export async function logoPreview(l: LogoSpec, scale = 2, signal?: AbortSignal): Promise<{ blob: Blob; ink: number }> {
  const fd = new FormData(); logoFields(fd, l); fd.append("scale", String(scale));
  const res = await fetchWithTimeout(apiUrl("/api/logo/preview"), { method: "POST", body: fd, signal });
  if (!res.ok) { let m = "logo error"; try { m = (await res.json()).detail; } catch { /* */ } throw new Error(m); }
  return { blob: await res.blob(), ink: Number(res.headers.get("x-ink-pixels") ?? 0) };
}

export const previewUrl = (id: string, max = 900) => apiUrl(`/api/image/${id}/preview?max=${max}`);
export const downloadUrl = (id: string) => apiUrl(`/api/image/${id}/download`);
export const health = () => call<{ ok: boolean }>("/api/health");

export function saveBlob(blob: Blob, name: string) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}
