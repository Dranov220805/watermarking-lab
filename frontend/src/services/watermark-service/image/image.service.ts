import { API_ROOT_PATH } from "@/src/@core/const";
import http from "@/src/@core/http";
import { get } from "@/src/@core/utils/get";
import type { ImageAssetOutputModel } from "./models/output.model";

const rootPath = get.rootPath(`${API_ROOT_PATH}/images`);

const uploadAsync = async (file: File): Promise<ImageAssetOutputModel> => {
  const formData = new FormData();
  formData.append("file", file);
  const result = await http.postForm<ImageAssetOutputModel>(`${rootPath}/upload`, formData);
  return result.data;
};

const getPreviewUrl = (imageId: string, max = 900): string =>
  `${rootPath}/${imageId}/preview?max=${max}`;

const getDownloadUrl = (imageId: string): string => `${rootPath}/${imageId}/download`;

export const imageService = { uploadAsync, getPreviewUrl, getDownloadUrl };
