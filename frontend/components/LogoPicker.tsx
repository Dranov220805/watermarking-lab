"use client";
import { useEffect, useRef, useState } from "react";
import { LogoSpec, logoPreview } from "@/lib/api";

type Source = LogoSpec["source"];

export default function LogoPicker({ onChange, title }: { onChange: (s: LogoSpec) => void; title: string }) {
  const [source, setSource] = useState<Source>("standard");
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("UNI");
  const [threshold, setThreshold] = useState(128);
  const [invert, setInvert] = useState(false);
  const [url, setUrl] = useState("");
  const [ink, setInk] = useState(0);
  const [err, setErr] = useState("");
  const cb = useRef(onChange);
  cb.current = onChange;

  useEffect(() => {
    const spec: LogoSpec = { source, text, threshold, invert, file };
    cb.current(spec);
    if (source === "upload" && !file) { setUrl(""); setInk(0); setErr(""); return; }
    const ac = new AbortController();
    const t = setTimeout(async () => {
      try {
        const { blob, ink } = await logoPreview(spec, 2, ac.signal);
        setUrl((old) => { if (old) URL.revokeObjectURL(old); return URL.createObjectURL(blob); });
        setInk(ink); setErr("");
      } catch (e) { if ((e as Error).name !== "AbortError") setErr((e as Error).message); }
    }, 200);
    return () => { clearTimeout(t); ac.abort(); };
  }, [source, file, text, threshold, invert]);

  return (
    <div className="logo-picker">
      <div className="row-label">{title}</div>
      <div className="seg">
        {(["standard", "upload", "text"] as Source[]).map((s) => (
          <button key={s} type="button" className={source === s ? "on" : ""} onClick={() => setSource(s)}>
            {s === "standard" ? "Standard logo" : s === "upload" ? "Upload image" : "Text"}
          </button>
        ))}
      </div>
      <div className="logo-row">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        {url ? <img src={url} alt="logo preview" className="logo-canvas" /> : <div className="logo-canvas" />}
        <div className="logo-controls">
          {source === "upload" && (
            <label className="file-btn">
              {file?.name || "Choose logo image…"}
              <input type="file" accept="image/*" hidden data-testid="logo-input"
                onChange={(e) => { setFile(e.target.files?.[0] ?? null); e.target.value = ""; }} />
            </label>
          )}
          {source === "text" && <input className="text-in" value={text} maxLength={10} onChange={(e) => setText(e.target.value)} placeholder="Text (max 10 chars)" />}
          {source !== "standard" && (
            <>
              <label className="slider">Threshold {threshold}
                <input type="range" min={20} max={235} value={threshold} onChange={(e) => setThreshold(+e.target.value)} />
              </label>
              <label className="check"><input type="checkbox" checked={invert} onChange={(e) => setInvert(e.target.checked)} /> Invert</label>
            </>
          )}
          <small>64×64 binary logo · {ink} ink pixels{url && (ink < 100 || ink > 3000) ? " · ⚠ adjust threshold" : ""}</small>
          {err && <small className="err">{err}</small>}
        </div>
      </div>
    </div>
  );
}
