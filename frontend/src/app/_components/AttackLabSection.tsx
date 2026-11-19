"use client";

import { useEffect, useState } from "react";
import SWTImagePicker from "@/src/@core/component/SWTImagePicker";
import SWTImagePreview from "@/src/@core/component/SWTImagePreview";
import SWTProgressBar from "@/src/@core/component/SWTProgressBar";
import useSWTMutation from "@/src/@core/hooks/useSWTMutation";
import type { ImageAssetOutputModel } from "@/src/services/watermark-service/image/models/output.model";
import type { AttackInputModel } from "@/src/services/watermark-service/operations/models/input.model";
import type { AttackOutputModel } from "@/src/services/watermark-service/operations/models/output.model";
import { watermarkService } from "@/src/services/watermark-service/watermark.service";

interface AttackLabSectionProps {
  sourceImage: ImageAssetOutputModel | null;
  onSourceImageChange: (asset: ImageAssetOutputModel) => void;
  onSendToExtract: (asset: ImageAssetOutputModel) => void;
}

export default function AttackLabSection({
  sourceImage,
  onSourceImageChange,
  onSendToExtract,
}: AttackLabSectionProps) {
  const [cropEnabled, setCropEnabled] = useState(true);
  const [crop, setCrop] = useState({ x: "0", y: "0", w: "0", h: "0" });
  const [noise, setNoise] = useState(0);
  const [jpegEnabled, setJpegEnabled] = useState(true);
  const [jpegQuality, setJpegQuality] = useState(70);

  const {
    mutation: runAttack,
    isLoading,
    data: attackResult,
    error,
    setError,
    reset,
  } = useSWTMutation<AttackOutputModel, AttackInputModel>({
    mutationFn: (input) => watermarkService.operationsService.attackAsync(input),
  });

  useEffect(() => {
    if (!sourceImage) return;
    reset();
    setCrop({
      x: String(((sourceImage.width / 4) | 0) + 3),
      y: String(((sourceImage.height / 4) | 0) + 5),
      w: String(Math.max(8, (sourceImage.width / 2) | 0)),
      h: String(Math.max(8, (sourceImage.height / 2) | 0)),
    });
  }, [sourceImage, reset]);

  function handleAttack() {
    if (!sourceImage) return;
    const cropSpec = cropEnabled
      ? { x: +crop.x, y: +crop.y, w: +crop.w, h: +crop.h }
      : null;
    if (cropSpec && ![cropSpec.x, cropSpec.y, cropSpec.w, cropSpec.h].every(Number.isInteger)) {
      setError("Crop values must be whole numbers.");
      return;
    }
    void runAttack({
      imageId: sourceImage.id,
      crop: cropSpec,
      noise,
      jpeg: jpegEnabled ? jpegQuality : 0,
    });
  }

  return (
    <section className="card" id="lab">
      <h2>
        <span className="step">2</span> Attack lab <small>(optional)</small>
      </h2>
      <SWTImagePicker
        label="Drop an image to attack, or use “Send to attack lab” above"
        onLoad={onSourceImageChange}
      />
      {sourceImage && (
        <>
          <div className="info">
            {sourceImage.name} · {sourceImage.width}×{sourceImage.height} · {sourceImage.format}
          </div>
          <div className="grid3">
            <fieldset>
              <legend>
                <label className="check">
                  <input
                    type="checkbox"
                    checked={cropEnabled}
                    onChange={(e) => setCropEnabled(e.target.checked)}
                  />{" "}
                  Crop
                </label>
              </legend>
              <div className="grid4">
                {(["x", "y", "w", "h"] as const).map((field) => (
                  <label key={field}>
                    {field}
                    <input
                      type="number"
                      value={crop[field]}
                      disabled={!cropEnabled}
                      onChange={(e) => setCrop({ ...crop, [field]: e.target.value })}
                      data-testid={`crop-${field}`}
                    />
                  </label>
                ))}
              </div>
              <small>Odd offsets (not multiples of 8) are the realistic case.</small>
            </fieldset>
            <fieldset>
              <legend>Gaussian noise</legend>
              <label className="slider">
                σ = {noise}
                <input
                  type="range"
                  min={0}
                  max={10}
                  step={0.5}
                  value={noise}
                  onChange={(e) => setNoise(+e.target.value)}
                />
              </label>
            </fieldset>
            <fieldset>
              <legend>
                <label className="check">
                  <input
                    type="checkbox"
                    checked={jpegEnabled}
                    onChange={(e) => setJpegEnabled(e.target.checked)}
                    data-testid="jpeg-on"
                  />{" "}
                  JPEG recompression
                </label>
              </legend>
              <label className="slider">
                Quality {jpegQuality}
                <input
                  type="range"
                  min={10}
                  max={100}
                  value={jpegQuality}
                  disabled={!jpegEnabled}
                  onChange={(e) => setJpegQuality(+e.target.value)}
                  data-testid="jpeg-q"
                />
              </label>
            </fieldset>
          </div>
          <div className="actions">
            <button
              className="primary"
              disabled={isLoading}
              onClick={handleAttack}
              data-testid="attack-btn"
            >
              Apply attacks
            </button>
          </div>
        </>
      )}
      {isLoading && <SWTProgressBar label="Attacking in Python" />}
      {error && <p className="err">{error}</p>}
      {attackResult && (
        <div className="result" data-testid="lab-result">
          <SWTImagePreview id={attackResult.id} max={600} />
          <div className="stats">
            <div>
              <b>Applied</b> {attackResult.desc}
            </div>
            <div>
              <b>Size</b> {attackResult.width}×{attackResult.height} · {attackResult.format}
            </div>
          </div>
          <div className="actions">
            <a
              className="btn"
              href={watermarkService.imageService.getDownloadUrl(attackResult.id)}
              download={attackResult.name}
            >
              Download {attackResult.format}
            </a>
            <button onClick={() => onSendToExtract(attackResult)} data-testid="lab-to-extract">
              Send to extract →
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
