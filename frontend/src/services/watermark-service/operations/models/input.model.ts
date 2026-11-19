export type WatermarkMethod = "dct" | "lsb";
export type ExtractMode = "search" | "aligned";
export type LogoSource = "standard" | "upload" | "text";

export interface LogoSpecModel {
  source: LogoSource;
  text: string;
  threshold: number;
  invert: boolean;
  file: File | null;
}

export interface CropSpecModel {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface LogoPreviewInputModel {
  logo: LogoSpecModel;
  scale?: number;
  signal?: AbortSignal;
}

export interface EmbedInputModel {
  imageId: string;
  key: string;
  alpha: number;
  method: WatermarkMethod;
  logo: LogoSpecModel;
}

export interface AttackInputModel {
  imageId: string;
  crop?: CropSpecModel | null;
  noise: number;
  jpeg: number;
}

export interface ExtractInputModel {
  imageId: string;
  key: string;
  alpha: number;
  method: WatermarkMethod;
  mode: ExtractMode;
  logo: LogoSpecModel;
}
