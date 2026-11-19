import { env } from "@/src/@core/config/env";

const rootPath = (path: string): string => `${env.apiUrl}${path}`;

export const get = { rootPath };
