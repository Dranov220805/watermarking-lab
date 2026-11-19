import { API_ROOT_PATH } from "@/src/@core/const";
import http from "@/src/@core/http";
import { get } from "@/src/@core/utils/get";
import type {
  AttackInputModel,
  EmbedInputModel,
  ExtractInputModel,
  LogoPreviewInputModel,
  LogoSpecModel,
} from "./models/input.model";
import type {
  AttackOutputModel,
  EmbedOutputModel,
  ExtractOutputModel,
  LogoPreviewOutputModel,
} from "./models/output.model";

const rootPath = get.rootPath(`${API_ROOT_PATH}/watermark`);

function appendLogoFields(formData: FormData, logo: LogoSpecModel): void {
  formData.append("logo_source", logo.source);
  formData.append("logo_text", logo.text);
  formData.append("logo_threshold", String(logo.threshold));
  formData.append("logo_invert", String(logo.invert));
  if (logo.source === "upload" && logo.file) {
    formData.append("logo_file", logo.file);
  }
}

const previewLogoAsync = async (
  input: LogoPreviewInputModel,
): Promise<LogoPreviewOutputModel> => {
  const formData = new FormData();
  appendLogoFields(formData, input.logo);
  formData.append("scale", String(input.scale ?? 2));
  const { blob, headers } = await http.postBlob(`${rootPath}/logo/preview`, formData, {
    signal: input.signal,
  });
  return { blob, ink: Number(headers.get("x-ink-pixels") ?? 0) };
};

const embedAsync = async (input: EmbedInputModel): Promise<EmbedOutputModel> => {
  const formData = new FormData();
  formData.append("image_id", input.imageId);
  formData.append("key", input.key);
  formData.append("alpha", String(input.alpha));
  formData.append("method", input.method);
  appendLogoFields(formData, input.logo);
  const result = await http.postForm<EmbedOutputModel>(`${rootPath}/embed`, formData);
  return result.data;
};

const attackAsync = async (input: AttackInputModel): Promise<AttackOutputModel> => {
  const formData = new FormData();
  formData.append("image_id", input.imageId);
  if (input.crop) {
    formData.append("crop_x", String(input.crop.x));
    formData.append("crop_y", String(input.crop.y));
    formData.append("crop_w", String(input.crop.w));
    formData.append("crop_h", String(input.crop.h));
  }
  formData.append("noise_sigma", String(input.noise));
  formData.append("jpeg_quality", String(input.jpeg));
  const result = await http.postForm<AttackOutputModel>(`${rootPath}/attack`, formData);
  return result.data;
};

const extractAsync = async (input: ExtractInputModel): Promise<ExtractOutputModel> => {
  const formData = new FormData();
  formData.append("image_id", input.imageId);
  formData.append("key", input.key);
  formData.append("alpha", String(input.alpha));
  formData.append("method", input.method);
  formData.append("mode", input.mode);
  appendLogoFields(formData, input.logo);
  const result = await http.postForm<ExtractOutputModel>(`${rootPath}/extract`, formData);
  return result.data;
};

export const operationsService = {
  previewLogoAsync,
  embedAsync,
  attackAsync,
  extractAsync,
};
