"use client";
import { previewUrl } from "@/lib/api";

export default function Preview({ id, max = 900 }: { id: string; max?: number }) {
  // eslint-disable-next-line @next/next/no-img-element
  return <img key={id} src={previewUrl(id, max)} alt="preview" className="preview" />;
}
