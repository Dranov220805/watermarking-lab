import { env } from "@/src/@core/config/env";
import type { ApiResult } from "./models/ApiResult";

const NETWORK_ERROR_MSG =
  "Cannot reach the Python backend. Start it with `npm run api` (or check API_PROXY_TARGET / NEXT_PUBLIC_API_URL in .env.local).";

async function extractErrorMessage(res: Response): Promise<string> {
  const msg = `${res.status} ${res.statusText}`;
  try {
    const body = await res.json();
    if (body?.error?.message && typeof body.error.message === "string") {
      return body.error.message;
    }
    if (typeof body?.message === "string" && body.message) {
      return body.message;
    }
    if (typeof body?.detail === "string") {
      return body.detail;
    }
    if (Array.isArray(body?.detail)) {
      return body.detail.map((d: { msg?: string }) => d.msg ?? "").filter(Boolean).join("; ") || msg;
    }
  } catch {
    // Keep default HTTP status message
  }
  return msg;
}

async function fetchWithTimeout(url: string, init?: RequestInit): Promise<Response> {
  const timeoutMs = env.requestTimeoutMs;
  if (!timeoutMs || timeoutMs <= 0) {
    return fetch(url, init);
  }

  const controller = new AbortController();
  const externalSignal = init?.signal;
  const onExternalAbort = () => controller.abort();
  if (externalSignal) {
    if (externalSignal.aborted) {
      controller.abort();
    } else {
      externalSignal.addEventListener("abort", onExternalAbort, { once: true });
    }
  }

  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);

  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } catch (err) {
    if (timedOut) {
      throw new Error(`Request timed out after ${Math.round(timeoutMs / 1000)}s.`);
    }
    throw err;
  } finally {
    clearTimeout(timer);
    if (externalSignal) {
      externalSignal.removeEventListener("abort", onExternalAbort);
    }
  }
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<ApiResult<T>> {
  let res: Response;
  try {
    res = await fetchWithTimeout(url, init);
  } catch (err) {
    if ((err as Error)?.name === "AbortError") {
      throw err;
    }
    if (err instanceof Error && err.message.startsWith("Request timed out")) {
      throw err;
    }
    throw new Error(NETWORK_ERROR_MSG);
  }

  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }

  const payload = (await res.json()) as ApiResult<T>;
  if (payload && payload.status === "error") {
    throw new Error(payload.error?.message || payload.message || "Unknown error.");
  }
  return payload;
}

async function requestBlob(
  url: string,
  init?: RequestInit,
): Promise<{ blob: Blob; headers: Headers }> {
  let res: Response;
  try {
    res = await fetchWithTimeout(url, init);
  } catch (err) {
    if ((err as Error)?.name === "AbortError") {
      throw err;
    }
    if (err instanceof Error && err.message.startsWith("Request timed out")) {
      throw err;
    }
    throw new Error(NETWORK_ERROR_MSG);
  }

  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }

  return { blob: await res.blob(), headers: res.headers };
}

const http = {
  get: <T>(url: string, init?: RequestInit) =>
    requestJson<T>(url, { ...init, method: "GET" }),

  postForm: <T>(url: string, formData: FormData, init?: RequestInit) =>
    requestJson<T>(url, { ...init, method: "POST", body: formData }),

  postBlob: (url: string, formData: FormData, init?: RequestInit) =>
    requestBlob(url, { ...init, method: "POST", body: formData }),
};

export default http;
