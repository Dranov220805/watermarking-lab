"use client";

import { useEffect, useRef, useState } from "react";
import { watermarkService } from "@/src/services/watermark-service/watermark.service";
import type {
  LogoSource,
  LogoSpecModel,
} from "@/src/services/watermark-service/operations/models/input.model";

interface SWTLogoPickerProps {
  onChange: (spec: LogoSpecModel) => void;
  title: string;
}

const SOURCES: { key: LogoSource; label: string }[] = [
  { key: "standard", label: "Standard logo" },
  { key: "upload", label: "Upload image" },
  { key: "text", label: "Text" },
];

export default function SWTLogoPicker({ onChange, title }: SWTLogoPickerProps) {
  const [source, setSource] = useState<LogoSource>("standard");
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("UNI");
  const [threshold, setThreshold] = useState(128);
  const [invert, setInvert] = useState(false);
  const [previewUrl, setPreviewUrl] = useState("");
  const [ink, setInk] = useState(0);
  const [error, setError] = useState("");
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  useEffect(() => {
    const spec: LogoSpecModel = { source, text, threshold, invert, file };
    onChangeRef.current(spec);

    if (source === "upload" && !file) {
      setPreviewUrl((old) => {
        if (old) URL.revokeObjectURL(old);
        return "";
      });
      setInk(0);
      setError("");
      return;
    }

    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const { blob, ink: inkPixels } =
          await watermarkService.operationsService.previewLogoAsync({
            logo: spec,
            scale: 2,
            signal: controller.signal,
          });
        setPreviewUrl((old) => {
          if (old) URL.revokeObjectURL(old);
          return URL.createObjectURL(blob);
        });
        setInk(inkPixels);
        setError("");
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setError((err as Error).message);
        }
      }
    }, 200);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [source, file, text, threshold, invert]);

  return (
    <div className="logo-picker">
      <div className="row-label">{title}</div>
      <div className="seg">
        {SOURCES.map((item) => (
          <button
            key={item.key}
            type="button"
            className={source === item.key ? "on" : ""}
            onClick={() => setSource(item.key)}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div className="logo-row">
        {previewUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={previewUrl} alt="logo preview" className="logo-canvas" />
        ) : (
          <div className="logo-canvas" />
        )}
        <div className="logo-controls">
          {source === "upload" && (
            <label className="file-btn">
              {file?.name || "Choose logo image…"}
              <input
                type="file"
                accept="image/*"
                hidden
                data-testid="logo-input"
                onChange={(e) => {
                  setFile(e.target.files?.[0] ?? null);
                  e.target.value = "";
                }}
              />
            </label>
          )}
          {source === "text" && (
            <input
              className="text-in"
              value={text}
              maxLength={10}
              onChange={(e) => setText(e.target.value)}
              placeholder="Text (max 10 chars)"
            />
          )}
          {source !== "standard" && (
            <>
              <label className="slider">
                Threshold {threshold}
                <input
                  type="range"
                  min={20}
                  max={235}
                  value={threshold}
                  onChange={(e) => setThreshold(+e.target.value)}
                />
              </label>
              <label className="check">
                <input
                  type="checkbox"
                  checked={invert}
                  onChange={(e) => setInvert(e.target.checked)}
                />{" "}
                Invert
              </label>
            </>
          )}
          <small>
            64×64 binary logo · {ink} ink pixels
            {previewUrl && (ink < 100 || ink > 3000) ? " · ⚠ adjust threshold" : ""}
          </small>
          {error && <small className="err">{error}</small>}
        </div>
      </div>
    </div>
  );
}
