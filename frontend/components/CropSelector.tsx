"use client";
import { useRef, useState } from "react";
import { ImgInfo, previewUrl } from "@/lib/api";

export interface CropRect {
  x: number;
  y: number;
  w: number;
  h: number;
}

type DragMode =
  | { kind: "draw"; startX: number; startY: number }
  | { kind: "move"; startX: number; startY: number; orig: CropRect }
  | { kind: "resize"; handle: "nw" | "ne" | "sw" | "se"; orig: CropRect };

const MIN_SIZE = 8;

function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v));
}

export default function CropSelector({
  image,
  crop,
  disabled,
  onChange,
}: {
  image: ImgInfo;
  crop: CropRect;
  disabled: boolean;
  onChange: (next: CropRect) => void;
}) {
  const stageRef = useRef<HTMLDivElement>(null);
  const [drag, setDrag] = useState<DragMode | null>(null);

  function toImageCoords(e: React.PointerEvent): { px: number; py: number } {
    const rect = stageRef.current!.getBoundingClientRect();
    const rx = clamp((e.clientX - rect.left) / rect.width, 0, 1);
    const ry = clamp((e.clientY - rect.top) / rect.height, 0, 1);
    return {
      px: Math.round(rx * image.width),
      py: Math.round(ry * image.height),
    };
  }

  function startDrag(e: React.PointerEvent, mode: DragMode) {
    if (disabled) return;
    e.preventDefault();
    e.stopPropagation();
    stageRef.current?.setPointerCapture(e.pointerId);
    setDrag(mode);
  }

  function onStagePointerDown(e: React.PointerEvent) {
    if (disabled) return;
    const { px, py } = toImageCoords(e);
    startDrag(e, { kind: "draw", startX: px, startY: py });
  }

  function onPointerMove(e: React.PointerEvent) {
    if (!drag || disabled) return;
    const { px, py } = toImageCoords(e);

    if (drag.kind === "draw") {
      const x1 = clamp(Math.min(drag.startX, px), 0, image.width - MIN_SIZE);
      const y1 = clamp(Math.min(drag.startY, py), 0, image.height - MIN_SIZE);
      const x2 = clamp(Math.max(drag.startX, px), x1 + MIN_SIZE, image.width);
      const y2 = clamp(Math.max(drag.startY, py), y1 + MIN_SIZE, image.height);
      onChange({ x: x1, y: y1, w: x2 - x1, h: y2 - y1 });
      return;
    }

    if (drag.kind === "move") {
      const dx = px - drag.startX;
      const dy = py - drag.startY;
      const nx = clamp(drag.orig.x + dx, 0, image.width - drag.orig.w);
      const ny = clamp(drag.orig.y + dy, 0, image.height - drag.orig.h);
      onChange({ x: nx, y: ny, w: drag.orig.w, h: drag.orig.h });
      return;
    }

    // Resize from corner handle
    const { orig, handle } = drag;
    let left = orig.x;
    let top = orig.y;
    let right = orig.x + orig.w;
    let bottom = orig.y + orig.h;

    if (handle.includes("w")) left = clamp(px, 0, right - MIN_SIZE);
    if (handle.includes("e")) right = clamp(px, left + MIN_SIZE, image.width);
    if (handle.includes("n")) top = clamp(py, 0, bottom - MIN_SIZE);
    if (handle.includes("s")) bottom = clamp(py, top + MIN_SIZE, image.height);

    onChange({ x: left, y: top, w: right - left, h: bottom - top });
  }

  function onPointerUp(e: React.PointerEvent) {
    if (!drag) return;
    if (stageRef.current?.hasPointerCapture(e.pointerId)) {
      stageRef.current.releasePointerCapture(e.pointerId);
    }
    setDrag(null);
  }

  function applyPreset(w: number, h: number, oddOffset = true) {
    const cw = Math.min(w, image.width);
    const ch = Math.min(h, image.height);
    let x = Math.floor((image.width - cw) / 2);
    let y = Math.floor((image.height - ch) / 2);
    if (oddOffset) {
      if (x % 8 === 0 && x + 3 + cw <= image.width) x += 3;
      if (y % 8 === 0 && y + 5 + ch <= image.height) y += 5;
    }
    onChange({ x: clamp(x, 0, image.width - cw), y: clamp(y, 0, image.height - ch), w: cw, h: ch });
  }

  const leftPct = (crop.x / image.width) * 100;
  const topPct = (crop.y / image.height) * 100;
  const widthPct = (crop.w / image.width) * 100;
  const heightPct = (crop.h / image.height) * 100;

  const blocks = Math.floor(crop.w / 8) * Math.floor(crop.h / 8);
  const copies = blocks / 4096;

  return (
    <div className={`crop-selector ${disabled ? "disabled" : ""}`} data-testid="crop-selector">
      <div
        ref={stageRef}
        className="crop-stage"
        onPointerDown={onStagePointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          key={image.id}
          src={previewUrl(image.id, 900)}
          alt="Drag to select crop region"
          className="crop-img"
          draggable={false}
        />
        {!disabled && (
          <div
            className="crop-box"
            style={{
              left: `${leftPct}%`,
              top: `${topPct}%`,
              width: `${widthPct}%`,
              height: `${heightPct}%`,
            }}
            onPointerDown={(e) => {
              const { px, py } = toImageCoords(e);
              startDrag(e, { kind: "move", startX: px, startY: py, orig: crop });
            }}
          >
            <div className="crop-dim-label">
              {crop.w}×{crop.h}
            </div>
            {(["nw", "ne", "sw", "se"] as const).map((h) => (
              <div
                key={h}
                className={`crop-handle ${h}`}
                onPointerDown={(e) => startDrag(e, { kind: "resize", handle: h, orig: crop })}
              />
            ))}
          </div>
        )}
      </div>

      <div className="crop-footer">
        <div className="crop-readout" data-testid="crop-readout">
          <b>Region</b> {crop.w}×{crop.h} px at ({crop.x}, {crop.y}) · {blocks.toLocaleString()} blocks ({copies.toFixed(1)} copies/bit)
          {copies < 1 && <span className="warnText"> — below 1 full copy/bit</span>}
        </div>
        <div className="crop-presets">
          <button type="button" disabled={disabled} onClick={() => applyPreset(Math.max(8, Math.floor(image.width / 2)), Math.max(8, Math.floor(image.height / 2)))}>
            Center 50%
          </button>
          <button type="button" disabled={disabled || image.width < 640 || image.height < 640} onClick={() => applyPreset(640, 640)}>
            640×640
          </button>
          <button type="button" disabled={disabled || image.width < 512 || image.height < 512} onClick={() => applyPreset(512, 512)}>
            512×512
          </button>
          <button type="button" disabled={disabled} onClick={() => applyPreset(image.width, image.height, false)}>
            Full
          </button>
        </div>
      </div>
      <small>Drag anywhere on the image to draw a region, drag inside the box to move, or drag corners to resize.</small>
    </div>
  );
}
