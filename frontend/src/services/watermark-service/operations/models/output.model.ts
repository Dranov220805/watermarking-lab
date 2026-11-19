import type { ImageAssetOutputModel } from "../../image/models/output.model";
import type { ExtractMode } from "./input.model";

export interface LogoPreviewOutputModel {
  blob: Blob;
  ink: number;
}

export interface EmbedOutputModel extends ImageAssetOutputModel {
  psnr: number | null;
  ssim: number | null;
  seconds: number;
}

export interface AttackOutputModel extends ImageAssetOutputModel {
  desc: string;
}

export interface ExtractOutputModel {
  mode: ExtractMode;
  blocks: number;
  copies: number;
  structure: number;
  structure_baseline: number;
  logo_png: string;
  seconds: number;
  nc?: number;
  ber?: number;
  score?: number;
  threshold?: number;
  null_mean?: number;
  null_max?: number;
  detected?: boolean;
  offset?: [number, number];
  phase?: [number, number];
}
