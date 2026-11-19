"use client";

import { watermarkService } from "@/src/services/watermark-service/watermark.service";

interface SWTImagePreviewProps {
  id: string;
  max?: number;
}

export default function SWTImagePreview({ id, max = 900 }: SWTImagePreviewProps) {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      key={id}
      src={watermarkService.imageService.getPreviewUrl(id, max)}
      alt="preview"
      className="preview"
    />
  );
}
