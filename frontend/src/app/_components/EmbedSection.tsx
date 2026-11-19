"use client";

import { useState } from "react";
import SWTImagePicker from "@/src/@core/component/SWTImagePicker";
import SWTImagePreview from "@/src/@core/component/SWTImagePreview";
import SWTLogoPicker from "@/src/@core/component/SWTLogoPicker";
import SWTProgressBar from "@/src/@core/component/SWTProgressBar";
import { STANDARD_LOGO } from "@/src/@core/const";
import useSWTMutation from "@/src/@core/hooks/useSWTMutation";
import { baseName, saveBlob } from "@/src/@core/utils/file";
import type { ImageAssetOutputModel } from "@/src/services/watermark-service/image/models/output.model";
import type {
  EmbedInputModel,
  LogoSpecModel,
  WatermarkMethod,
} from "@/src/services/watermark-service/operations/models/input.model";
import type { EmbedOutputModel } from "@/src/services/watermark-service/operations/models/output.model";
import { watermarkService } from "@/src/services/watermark-service/watermark.service";

interface EmbedSectionProps {
  secretKey: string;
  alpha: number;
  method: WatermarkMethod;
  onSendToLab: (asset: ImageAssetOutputModel) => void;
  onSendToExtract: (asset: ImageAssetOutputModel) => void;
}

export default function EmbedSection({
  secretKey,
  alpha,
  method,
  onSendToLab,
  onSendToExtract,
}: EmbedSectionProps) {
  const [sourceImage, setSourceImage] = useState<ImageAssetOutputModel | null>(null);
  const [embedLogo, setEmbedLogo] = useState<LogoSpecModel>(STANDARD_LOGO);

  const {
    mutation: runEmbed,
    isLoading,
    data: embedResult,
    error,
    reset,
  } = useSWTMutation<EmbedOutputModel, EmbedInputModel>({
    mutationFn: (input) => watermarkService.operationsService.embedAsync(input),
  });

  function handleEmbed() {
    if (!sourceImage) return;
    void runEmbed({
      imageId: sourceImage.id,
      key: secretKey,
      alpha,
      method,
      logo: embedLogo,
    });
  }

  async function handleDownloadReferenceLogo() {
    if (!embedResult) return;
    const { blob } = await watermarkService.operationsService.previewLogoAsync({
      logo: embedLogo,
      scale: 1,
    });
    saveBlob(blob, `${baseName(embedResult.name)}_logo64.png`);
  }

  return (
    <section className="card" id="embed">
      <h2>
        <span className="step">1</span> Embed watermark
      </h2>
      <SWTImagePicker
        label="Drop a cover image here or click to choose"
        onLoad={(asset) => {
          setSourceImage(asset);
          reset();
        }}
      />
      {sourceImage && (
        <div className="info" data-testid="src-info">
          <b>{sourceImage.name}</b> · {sourceImage.width}×{sourceImage.height} ·{" "}
          {sourceImage.format} · {sourceImage.copies.toFixed(1)} copies of each logo bit
          {sourceImage.copies < 1 && (
            <span className="err"> — too small (need ≈512×512 px or more)</span>
          )}
          {sourceImage.copies >= 1 && sourceImage.copies < 4 && (
            <span className="warnText"> — low redundancy, weak against crops/JPEG</span>
          )}
        </div>
      )}
      <SWTLogoPicker title="Watermark logo" onChange={setEmbedLogo} />
      <div className="actions">
        <button
          className="primary"
          disabled={!sourceImage || isLoading}
          onClick={handleEmbed}
          data-testid="embed-btn"
        >
          Embed watermark
        </button>
      </div>
      {isLoading && <SWTProgressBar label="Embedding in Python" />}
      {error && <p className="err">{error}</p>}
      {embedResult && (
        <div className="result" data-testid="embed-result">
          <SWTImagePreview id={embedResult.id} />
          <div className="stats">
            <div>
              <b>PSNR</b> {embedResult.psnr != null ? `${embedResult.psnr.toFixed(2)} dB` : "∞"}
            </div>
            <div>
              <b>SSIM</b>{" "}
              {embedResult.ssim != null ? embedResult.ssim.toFixed(4) : "skipped (large image)"}
            </div>
            <div>
              <b>Redundancy</b> {embedResult.copies.toFixed(1)} copies/bit
            </div>
            <div>
              <b>Time</b> {embedResult.seconds}s
            </div>
          </div>
          <p className="hint">
            Output is lossless PNG. Never re-save as JPEG: that is an attack. Remember key{" "}
            <code>{secretKey}</code>, α = {alpha}, method {method.toUpperCase()}.
          </p>
          <div className="actions">
            <a
              className="btn"
              href={watermarkService.imageService.getDownloadUrl(embedResult.id)}
              download={embedResult.name}
              data-testid="dl-wm"
            >
              Download PNG
            </a>
            <button onClick={() => void handleDownloadReferenceLogo()}>
              Download logo (64×64 reference)
            </button>
            <button onClick={() => onSendToLab(embedResult)} data-testid="to-lab">
              Send to attack lab →
            </button>
            <button onClick={() => onSendToExtract(embedResult)} data-testid="to-extract">
              Send to extract →
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
