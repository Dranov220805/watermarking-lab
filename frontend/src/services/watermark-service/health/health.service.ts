import { API_ROOT_PATH } from "@/src/@core/const";
import http from "@/src/@core/http";
import { get } from "@/src/@core/utils/get";
import type { HealthOutputModel } from "./models/output.model";

const rootPath = get.rootPath(API_ROOT_PATH);

const checkHealthAsync = async (): Promise<HealthOutputModel> => {
  const result = await http.get<HealthOutputModel>(`${rootPath}/health`);
  return result.data;
};

export const healthService = { checkHealthAsync };
