"use client";
import { useRef, useState } from "react";
import { ImgInfo, upload } from "@/lib/api";

export default function ImagePicker({ onLoad, label }: { onLoad: (i: ImgInfo) => void; label: string }) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [drag, setDrag] = useState(false);

  async function handle(file?: File) {
    if (!file) return;
    setErr(""); setBusy(true);
    try { onLoad(await upload(file)); }
    catch (e) { setErr(e instanceof Error ? e.message : "upload failed"); }
    finally { setBusy(false); }
  }

  return (
    <div>
      <div className={`drop ${drag ? "drag" : ""}`} role="button" tabIndex={0}
        onClick={() => input.current?.click()}
        onKeyDown={(e) => { if (e.key === "Enter") input.current?.click(); }}
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); handle(e.dataTransfer.files[0]); }}>
        {busy ? "Uploading and decoding…" : label}
        <small>PNG · JPEG · WebP · BMP · GIF · TIFF</small>
      </div>
      <input ref={input} type="file" hidden data-testid="file-input"
        accept="image/png,image/jpeg,image/webp,image/bmp,image/gif,image/tiff,.png,.jpg,.jpeg,.webp,.bmp,.gif,.tif,.tiff"
        onChange={(e) => { handle(e.target.files?.[0]); e.target.value = ""; }} />
      {err && <p className="err">{err}</p>}
    </div>
  );
}
