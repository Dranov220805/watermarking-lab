import type { ExtractOutputModel } from "@/src/services/watermark-service/operations/models/output.model";

export interface ExtractVerdict {
  cls: "good" | "warn" | "bad";
  text: string;
}

export function evaluateExtractVerdict(result: ExtractOutputModel | null): ExtractVerdict | null {
  if (!result) return null;

  if (result.mode === "search") {
    if (!result.detected) {
      return {
        cls: "bad",
        text: "No watermark found for this key, logo and settings (score below the false-positive threshold).",
      };
    }
    if ((result.ber ?? 1) < 0.02) {
      return { cls: "good", text: "Watermark recovered intact." };
    }
    if ((result.ber ?? 1) < 0.15) {
      return { cls: "warn", text: "Watermark recovered with minor damage." };
    }
    return {
      cls: "warn",
      text: "Watermark pattern detected, but the logo is heavily damaged (strong compression, noise or small crop).",
    };
  }

  return result.structure - result.structure_baseline >= 0.12
    ? {
        cls: "good",
        text: "A clear logo-like structure was extracted. Key and settings look correct for this uncropped image.",
      }
    : {
        cls: "bad",
        text: "Output looks like noise: wrong key/settings, no watermark, image cropped (use search mode), or compression too strong.",
      };
}
