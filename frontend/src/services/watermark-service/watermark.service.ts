import { API_ROOT_PATH } from "@/src/@core/const";
import { get } from "@/src/@core/utils/get";
import { healthService } from "./health/health.service";
import { imageService } from "./image/image.service";
import { operationsService } from "./operations/operations.service";

export const rootPath: string = get.rootPath(API_ROOT_PATH);

export const watermarkService = {
  healthService,
  imageService,
  operationsService,
};
