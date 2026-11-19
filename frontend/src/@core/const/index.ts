import { env } from "@/src/@core/config/env";
import type { LogoSpecModel } from "@/src/services/watermark-service/operations/models/input.model";

export const DEFAULT_ALPHA = env.defaultAlpha;
export const DEFAULT_SECRET_KEY = env.defaultSecretKey;
export const DEFAULT_METHOD = env.defaultMethod;

export const API_ROOT_PATH = env.apiPrefix;

export const ACCEPTED_IMAGE_TYPES =
  "image/png,image/jpeg,image/webp,image/bmp,image/gif,image/tiff,.png,.jpg,.jpeg,.webp,.bmp,.gif,.tif,.tiff";

export const STANDARD_LOGO: LogoSpecModel = {
  source: "standard",
  text: "",
  threshold: 128,
  invert: false,
  file: null,
};
