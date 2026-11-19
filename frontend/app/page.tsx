"use client";
import { useEffect, useMemo, useState } from "react";
import ImagePicker from "@/components/ImagePicker";
import LogoPicker from "@/components/LogoPicker";
import Preview from "@/components/Preview";
import {
  AttackOut, EmbedOut, ExtractOut, ImgInfo, LogoSpec, Method, Mode, STANDARD_LOGO,
  attack, downloadUrl, embed, extract, health, logoPreview, saveBlob,
} from "@/lib/api";

const DEFAULT_ALPHA = 25;
const scrollTo = (id: string) => setTimeout(() => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
const base = (n: string) => n.replace(/\.[^.]+$/, "") || "image";

function Busy({ label }: { label: string }) {
  const [s, setS] = useState(0);
  useEffect(() => { const t = setInterval(() => setS((v) => v + 1), 1000); return () => clearInterval(t); }, []);
  return <div className="progress" role="status"><div className="bar indeterminate"><div /></div><span>{label}… {s}s</span></div>;
}

export default function Home() {
  const [backend, setBackend] = useState<"checking" | "ok" | "down">("checking");
  useEffect(() => { health().then(() => setBackend("ok")).catch(() => setBackend("down")); }, []);

  const [key, setKey] = useState("my-secret-key");
  const [alpha, setAlpha] = useState(DEFAULT_ALPHA);
  const [method, setMethod] = useState<Method>("dct");

  // embed
  const [src, setSrc] = useState<ImgInfo | null>(null);
  const [embLogo, setEmbLogo] = useState<LogoSpec>(STANDARD_LOGO);
  const [emb, setEmb] = useState<EmbedOut | null>(null);
  const [embErr, setEmbErr] = useState("");
  const [embBusy, setEmbBusy] = useState(false);

  // lab
  const [lab, setLab] = useState<ImgInfo | null>(null);
  const [cropOn, setCropOn] = useState(true);
  const [crop, setCrop] = useState({ x: "0", y: "0", w: "0", h: "0" });
  const [noise, setNoise] = useState(0);
  const [jpegOn, setJpegOn] = useState(true);
  const [jpegQ, setJpegQ] = useState(70);
  const [labOut, setLabOut] = useState<AttackOut | null>(null);
  const [labErr, setLabErr] = useState("");
  const [labBusy, setLabBusy] = useState(false);

  // extract
  const [ex, setEx] = useState<ImgInfo | null>(null);
  const [mode, setMode] = useState<Mode>("search");
  const [refLogo, setRefLogo] = useState<LogoSpec>(STANDARD_LOGO);
  const [exRes, setExRes] = useState<ExtractOut | null>(null);
  const [exErr, setExErr] = useState("");
  const [exBusy, setExBusy] = useState(false);

  function setLabSource(i: ImgInfo) {
    setLab(i); setLabOut(null); setLabErr("");
    setCrop({ x: String(((i.width / 4) | 0) + 3), y: String(((i.height / 4) | 0) + 5), w: String(Math.max(8, (i.width / 2) | 0)), h: String(Math.max(8, (i.height / 2) | 0)) });
  }
  function setExSource(i: ImgInfo) { setEx(i); setExRes(null); setExErr(""); }

  async function doEmbed() {
    if (!src) return;
    setEmbErr(""); setEmb(null); setEmbBusy(true);
    try { setEmb(await embed({ imageId: src.id, key, alpha, method, logo: embLogo })); }
    catch (e) { setEmbErr((e as Error).message); }
    finally { setEmbBusy(false); }
  }

  async function doAttack() {
    if (!lab) return;
    setLabErr(""); setLabOut(null); setLabBusy(true);
    try {
      const c = cropOn ? { x: +crop.x, y: +crop.y, w: +crop.w, h: +crop.h } : null;
      if (c && ![c.x, c.y, c.w, c.h].every(Number.isInteger)) throw new Error("Crop values must be whole numbers.");
      setLabOut(await attack({ imageId: lab.id, crop: c, noise, jpeg: jpegOn ? jpegQ : 0 }));
    } catch (e) { setLabErr((e as Error).message); }
    finally { setLabBusy(false); }
  }

  async function doExtract() {
    if (!ex) return;
    setExErr(""); setExRes(null); setExBusy(true);
    try { setExRes(await extract({ imageId: ex.id, key, alpha, method, mode, logo: refLogo })); }
    catch (e) { setExErr((e as Error).message); }
    finally { setExBusy(false); }
  }

  const verdict = useMemo(() => {
    if (!exRes) return null;
    if (exRes.mode === "search") {
      if (!exRes.detected) return { cls: "bad", text: "No watermark found for this key, logo and settings (score below the false-positive threshold)." };
      if (exRes.ber! < 0.02) return { cls: "good", text: "Watermark recovered intact." };
      if (exRes.ber! < 0.15) return { cls: "warn", text: "Watermark recovered with minor damage." };
      return { cls: "warn", text: "Watermark pattern detected, but the logo is heavily damaged (strong compression, noise or small crop)." };
    }
    return exRes.structure - exRes.structure_baseline >= 0.12
      ? { cls: "good", text: "A clear logo-like structure was extracted. Key and settings look correct for this uncropped image." }
      : { cls: "bad", text: "Output looks like noise: wrong key/settings, no watermark, image cropped (use search mode), or compression too strong." };
  }, [exRes]);

  return (
    <main>
      <header>
        <h1>DCT Watermarking Lab</h1>
        <p>Embed a copyright logo in the frequency domain, attack the image (JPEG, crop, noise), then extract it again.
          All algorithm steps run in the Python backend (NumPy / OpenCV); this page is the interface.</p>
        {backend === "down" && <p className="err banner" data-testid="backend-down">Python backend not reachable. Start it with <code>npm run api</code> (port 8000), or use <code>npm run dev:all</code>.</p>}
      </header>

      <section className="card" id="settings">
        <h2>Settings <small>(shared by embed and extract)</small></h2>
        <div className="grid3">
          <label>Secret key
            <input value={key} onChange={(e) => setKey(e.target.value)} data-testid="key" />
          </label>
          <label>Strength α = {alpha}
            <input type="range" min={10} max={60} value={alpha} onChange={(e) => setAlpha(+e.target.value)} data-testid="alpha" />
            <small>Higher: survives stronger JPEG, but lower image quality.</small>
          </label>
          <label>Method
            <select value={method} onChange={(e) => setMethod(e.target.value as Method)} data-testid="method">
              <option value="dct">DCT mid-frequency (robust)</option>
              <option value="lsb">LSB spatial (baseline, fragile)</option>
            </select>
            <small>Use LSB to see why the spatial domain fails under JPEG.</small>
          </label>
        </div>
      </section>

      <section className="card" id="embed">
        <h2><span className="step">1</span> Embed watermark</h2>
        <ImagePicker label="Drop a cover image here or click to choose" onLoad={(i) => { setSrc(i); setEmb(null); setEmbErr(""); }} />
        {src && (
          <div className="info" data-testid="src-info">
            <b>{src.name}</b> · {src.width}×{src.height} · {src.format} · {src.copies.toFixed(1)} copies of each logo bit
            {src.copies < 1 && <span className="err"> — too small (need ≈512×512 px or more)</span>}
            {src.copies >= 1 && src.copies < 4 && <span className="warnText"> — low redundancy, weak against crops/JPEG</span>}
          </div>
        )}
        <LogoPicker title="Watermark logo" onChange={setEmbLogo} />
        <div className="actions">
          <button className="primary" disabled={!src || embBusy} onClick={doEmbed} data-testid="embed-btn">Embed watermark</button>
        </div>
        {embBusy && <Busy label="Embedding in Python" />}
        {embErr && <p className="err">{embErr}</p>}
        {emb && (
          <div className="result" data-testid="embed-result">
            <Preview id={emb.id} />
            <div className="stats">
              <div><b>PSNR</b> {emb.psnr != null ? emb.psnr.toFixed(2) + " dB" : "∞"}</div>
              <div><b>SSIM</b> {emb.ssim != null ? emb.ssim.toFixed(4) : "skipped (large image)"}</div>
              <div><b>Redundancy</b> {emb.copies.toFixed(1)} copies/bit</div>
              <div><b>Time</b> {emb.seconds}s</div>
            </div>
            <p className="hint">Output is lossless PNG. Never re-save as JPEG: that is an attack. Remember key <code>{key}</code>, α = {alpha}, method {method.toUpperCase()}.</p>
            <div className="actions">
              <a className="btn" href={downloadUrl(emb.id)} download={emb.name} data-testid="dl-wm">Download PNG</a>
              <button onClick={async () => saveBlob((await logoPreview(embLogo, 1)).blob, `${base(emb.name)}_logo64.png`)}>Download logo (64×64 reference)</button>
              <button onClick={() => { setLabSource(emb); scrollTo("lab"); }} data-testid="to-lab">Send to attack lab →</button>
              <button onClick={() => { setExSource(emb); scrollTo("extract"); }} data-testid="to-extract">Send to extract →</button>
            </div>
          </div>
        )}
      </section>

      <section className="card" id="lab">
        <h2><span className="step">2</span> Attack lab <small>(optional)</small></h2>
        <ImagePicker label="Drop an image to attack, or use “Send to attack lab” above" onLoad={setLabSource} />
        {lab && (
          <>
            <div className="info">{lab.name} · {lab.width}×{lab.height} · {lab.format}</div>
            <div className="grid3">
              <fieldset>
                <legend><label className="check"><input type="checkbox" checked={cropOn} onChange={(e) => setCropOn(e.target.checked)} /> Crop</label></legend>
                <div className="grid4">
                  {(["x", "y", "w", "h"] as const).map((k) => (
                    <label key={k}>{k}<input type="number" value={crop[k]} disabled={!cropOn}
                      onChange={(e) => setCrop({ ...crop, [k]: e.target.value })} data-testid={`crop-${k}`} /></label>
                  ))}
                </div>
                <small>Odd offsets (not multiples of 8) are the realistic case.</small>
              </fieldset>
              <fieldset>
                <legend>Gaussian noise</legend>
                <label className="slider">σ = {noise}<input type="range" min={0} max={10} step={0.5} value={noise} onChange={(e) => setNoise(+e.target.value)} /></label>
              </fieldset>
              <fieldset>
                <legend><label className="check"><input type="checkbox" checked={jpegOn} onChange={(e) => setJpegOn(e.target.checked)} data-testid="jpeg-on" /> JPEG recompression</label></legend>
                <label className="slider">Quality {jpegQ}<input type="range" min={10} max={100} value={jpegQ} disabled={!jpegOn}
                  onChange={(e) => setJpegQ(+e.target.value)} data-testid="jpeg-q" /></label>
              </fieldset>
            </div>
            <div className="actions">
              <button className="primary" disabled={labBusy} onClick={doAttack} data-testid="attack-btn">Apply attacks</button>
            </div>
          </>
        )}
        {labBusy && <Busy label="Attacking in Python" />}
        {labErr && <p className="err">{labErr}</p>}
        {labOut && (
          <div className="result" data-testid="lab-result">
            <Preview id={labOut.id} max={600} />
            <div className="stats"><div><b>Applied</b> {labOut.desc}</div><div><b>Size</b> {labOut.width}×{labOut.height} · {labOut.format}</div></div>
            <div className="actions">
              <a className="btn" href={downloadUrl(labOut.id)} download={labOut.name}>Download {labOut.format}</a>
              <button onClick={() => { setExSource(labOut); scrollTo("extract"); }} data-testid="lab-to-extract">Send to extract →</button>
            </div>
          </div>
        )}
      </section>

      <section className="card" id="extract">
        <h2><span className="step">3</span> Extract watermark</h2>
        <ImagePicker label="Drop a suspect image here or use “Send to extract”" onLoad={setExSource} />
        {ex && <div className="info" data-testid="ex-info">{ex.name} · {ex.width}×{ex.height} · {ex.format} · {ex.copies.toFixed(1)} copies/bit</div>}
        <div className="modes">
          <label className={mode === "search" ? "on" : ""}>
            <input type="radio" name="mode" checked={mode === "search"} onChange={() => { setMode("search"); setExRes(null); }} data-testid="mode-search" />
            <b>Search (needs the original logo)</b>
            <small>Finds grid offset and tile position. Works on cropped images and gives a detection score against false positives.</small>
          </label>
          <label className={mode === "aligned" ? "on" : ""}>
            <input type="radio" name="mode" checked={mode === "aligned"} onChange={() => { setMode("aligned"); setExRes(null); }} data-testid="mode-aligned" />
            <b>Aligned (key only)</b>
            <small>No logo needed, but the image must be uncropped (JPEG, noise are fine). You judge the result by eye.</small>
          </label>
        </div>
        {mode === "search" && <LogoPicker title="Reference logo (the one you embedded)" onChange={setRefLogo} />}
        <div className="actions">
          <button className="primary" disabled={!ex || exBusy} onClick={doExtract} data-testid="extract-btn">Extract watermark</button>
        </div>
        {exBusy && <Busy label="Extracting in Python" />}
        {exErr && <p className="err">{exErr}</p>}
        {exRes && verdict && (
          <div className="result" data-testid="extract-result">
            <div className={`verdict ${verdict.cls}`} data-testid="verdict">{verdict.text}</div>
            <div className="ex-row">
              <div>
                <div className="row-label">Extracted logo</div>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={exRes.logo_png} alt="extracted logo" className="logo-canvas big" data-testid="extracted-logo" />
              </div>
              <table className="stat-table">
                <tbody>
                  {exRes.mode === "search" ? (
                    <>
                      <tr><td>NC</td><td data-testid="nc">{exRes.nc!.toFixed(3)}</td></tr>
                      <tr><td>BER</td><td data-testid="ber">{(exRes.ber! * 100).toFixed(1)} %</td></tr>
                      <tr><td>Detection score</td><td>{exRes.score!.toFixed(3)} (threshold {exRes.threshold!.toFixed(3)}, wrong-key max {exRes.null_max!.toFixed(3)})</td></tr>
                      <tr><td>Grid offset (x,y)</td><td>{exRes.offset!.join(", ")}</td></tr>
                      <tr><td>Tile position</td><td>{exRes.phase!.join(", ")}</td></tr>
                    </>
                  ) : (
                    <tr><td>Structure score</td><td data-testid="structure">{(exRes.structure * 100).toFixed(0)} % (a random scramble of the same pixels gives ≈{(exRes.structure_baseline * 100).toFixed(0)} %)</td></tr>
                  )}
                  <tr><td>Redundancy</td><td>{exRes.copies.toFixed(1)} copies/bit</td></tr>
                  <tr><td>Time</td><td>{exRes.seconds}s</td></tr>
                </tbody>
              </table>
            </div>
            <div className="actions">
              <a className="btn" href={exRes.logo_png} download={`${base(ex!.name)}_extracted_logo.png`}>Download extracted logo</a>
            </div>
          </div>
        )}
      </section>

      <footer>
        <h3>Limits (see report)</h3>
        <ul>
          <li>Robust to JPEG down to roughly Q≈50 at α=25 and to crops that still hold enough 8×8 blocks (≥ 4096 blocks ≈ 512×512 px for one copy of every bit). Not to resize, rotation or perspective change.</li>
          <li>Search mode is hypothesis-guided: it needs key and reference logo. Detection threshold = mean + 6σ of a wrong-key null distribution measured on the suspect image (mean-centred correlation).</li>
          <li>Uploaded images are kept by the Python backend in a temp folder and deleted after 2 hours. Transparency is flattened onto white; embed output is always PNG.</li>
          <li>Research demo. A robust watermark shows origin, not that an image is unmodified.</li>
        </ul>
      </footer>
    </main>
  );
}
