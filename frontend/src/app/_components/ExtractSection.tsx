"use client";

import { useEffect, useMemo, useState } from "react";
import SWTImagePicker from "@/src/@core/component/SWTImagePicker";
import SWTLogoPicker from "@/src/@core/component/SWTLogoPicker";
import SWTProgressBar from "@/src/@core/component/SWTProgressBar";
import { STANDARD_LOGO } from "@/src/@core/const";
import useSWTMutation from "@/src/@core/hooks/useSWTMutation";
import { baseName } from "@/src/@core/utils/file";
import type { ImageAssetOutputModel } from "@/src/services/watermark-service/image/models/output.model";
import type {
  ExtractInputModel,
  ExtractMode,
  LogoSpecModel,
  WatermarkMethod,
} from "@/src/services/watermark-service/operations/models/input.model";
import type { ExtractOutputModel } from "@/src/services/watermark-service/operations/models/output.model";
import { watermarkService } from "@/src/services/watermark-service/watermark.service";
import { evaluateExtractVerdict } from "./verdict";

interface ExtractSectionProps {
  sourceImage: ImageAssetOutputModel | null;
  secretKey: string;
  alpha: number;
  method: WatermarkMethod;
  onSourceImageChange: (asset: ImageAssetOutputModel) => void;
}

export default function ExtractSection({
  sourceImage,
  secretKey,
  alpha,
  method,
  onSourceImageChange,
}: ExtractSectionProps) {
  const [mode, setMode] = useState<ExtractMode>("search");
  const [refLogo, setRefLogo] = useState<LogoSpecModel>(STANDARD_LOGO);

  const {
    mutation: runExtract,
    isLoading,
    data: extractResult,
    error,
    reset,
  } = useSWTMutation<ExtractOutputModel, ExtractInputModel>({
    mutationFn: (input) => watermarkService.operationsService.extractAsync(input),
  });

  useEffect(() => {
    reset();
  }, [sourceImage, reset]);

  const verdict = useMemo(() => evaluateExtractVerdict(extractResult), [extractResult]);

  function handleExtract() {
    if (!sourceImage) return;
    void runExtract({
      imageId: sourceImage.id,
      key: secretKey,
      alpha,
      method,
      mode,
      logo: refLogo,
    });
  }

  return (
    <section className="card" id="extract">
      <h2>
        <span className="step">3</span> Extract watermark
      </h2>
      <SWTImagePicker
        label="Drop a suspect image here or use “Send to extract”"
        onLoad={onSourceImageChange}
      />
      {sourceImage && (
        <div className="info" data-testid="ex-info">
          {sourceImage.name} · {sourceImage.width}×{sourceImage.height} · {sourceImage.format} ·{" "}
          {sourceImage.copies.toFixed(1)} copies/bit
        </div>
      )}
      <div className="modes">
        <label className={mode === "search" ? "on" : ""}>
          <input
            type="radio"
            name="mode"
            checked={mode === "search"}
            onChange={() => {
              setMode("search");
              reset();
            }}
            data-testid="mode-search"
          />
          <b>Search (needs the original logo)</b>
          <small>
            Finds grid offset and tile position. Works on cropped images and gives a detection
            score against false positives.
          </small>
        </label>
        <label className={mode === "aligned" ? "on" : ""}>
          <input
            type="radio"
            name="mode"
            checked={mode === "aligned"}
            onChange={() => {
              setMode("aligned");
              reset();
            }}
            data-testid="mode-aligned"
          />
          <b>Aligned (key only)</b>
          <small>
            No logo needed, but the image must be uncropped (JPEG, noise are fine). You judge the
            result by eye.
          </small>
        </label>
      </div>
      {mode === "search" && (
        <SWTLogoPicker title="Reference logo (the one you embedded)" onChange={setRefLogo} />
      )}
      <div className="actions">
        <button
          className="primary"
          disabled={!sourceImage || isLoading}
          onClick={handleExtract}
          data-testid="extract-btn"
        >
          Extract watermark
        </button>
      </div>
      {isLoading && <SWTProgressBar label="Extracting in Python" />}
      {error && <p className="err">{error}</p>}
      {extractResult && verdict && (
        <div className="result" data-testid="extract-result">
          <div className={`verdict ${verdict.cls}`} data-testid="verdict">
            {verdict.text}
          </div>
          <div className="ex-row">
            <div>
              <div className="row-label">Extracted logo</div>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={extractResult.logo_png}
                alt="extracted logo"
                className="logo-canvas big"
                data-testid="extracted-logo"
              />
            </div>
            <table className="stat-table">
              <tbody>
                {extractResult.mode === "search" ? (
                  <>
                    <tr>
                      <td>NC</td>
                      <td data-testid="nc">{extractResult.nc!.toFixed(3)}</td>
                    </tr>
                    <tr>
                      <td>BER</td>
                      <td data-testid="ber">{(extractResult.ber! * 100).toFixed(1)} %</td>
                    </tr>
                    <tr>
                      <td>Detection score</td>
                      <td>
                        {extractResult.score!.toFixed(3)} (threshold{" "}
                        {extractResult.threshold!.toFixed(3)}, wrong-key max{" "}
                        {extractResult.null_max!.toFixed(3)})
                      </td>
                    </tr>
                    <tr>
                      <td>Grid offset (x,y)</td>
                      <td>{extractResult.offset!.join(", ")}</td>
                    </tr>
                    <tr>
                      <td>Tile position</td>
                      <td>{extractResult.phase!.join(", ")}</td>
                    </tr>
                  </>
                ) : (
                  <tr>
                    <td>Structure score</td>
                    <td data-testid="structure">
                      {(extractResult.structure * 100).toFixed(0)} % (a random scramble of the same
                      pixels gives ≈{(extractResult.structure_baseline * 100).toFixed(0)} %)
                    </td>
                  </tr>
                )}
                <tr>
                  <td>Redundancy</td>
                  <td>{extractResult.copies.toFixed(1)} copies/bit</td>
                </tr>
                <tr>
                  <td>Time</td>
                  <td>{extractResult.seconds}s</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div className="actions">
            <a
              className="btn"
              href={extractResult.logo_png}
              download={`${baseName(sourceImage!.name)}_extracted_logo.png`}
            >
              Download extracted logo
            </a>
          </div>
        </div>
      )}
    </section>
  );
}
