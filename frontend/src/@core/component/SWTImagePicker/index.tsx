"use client";

import { useRef, useState } from "react";
import { ACCEPTED_IMAGE_TYPES } from "@/src/@core/const";
import useSWTMutation from "@/src/@core/hooks/useSWTMutation";
import { watermarkService } from "@/src/services/watermark-service/watermark.service";
import type { ImageAssetOutputModel } from "@/src/services/watermark-service/image/models/output.model";

interface SWTImagePickerProps {
  onLoad: (asset: ImageAssetOutputModel) => void;
  label: string;
}

export default function SWTImagePicker({ onLoad, label }: SWTImagePickerProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const { mutation: uploadFile, isLoading, error } = useSWTMutation<ImageAssetOutputModel, File>({
    mutationFn: (file) => watermarkService.imageService.uploadAsync(file),
    onSuccess: (res) => {
      if (res) onLoad(res);
    },
  });

  function handleFile(file?: File) {
    if (!file) return;
    void uploadFile(file);
  }

  return (
    <div>
      <div
        className={`drop ${isDragging ? "drag" : ""}`}
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter") inputRef.current?.click();
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          handleFile(e.dataTransfer.files[0]);
        }}
      >
        {isLoading ? "Uploading and decoding…" : label}
        <small>PNG · JPEG · WebP · BMP · GIF · TIFF</small>
      </div>
      <input
        ref={inputRef}
        type="file"
        hidden
        data-testid="file-input"
        accept={ACCEPTED_IMAGE_TYPES}
        onChange={(e) => {
          handleFile(e.target.files?.[0]);
          e.target.value = "";
        }}
      />
      {error && <p className="err">{error}</p>}
    </div>
  );
}
