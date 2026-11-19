"use client";

import type { ReactNode } from "react";
import { env } from "@/src/@core/config/env";

interface MainLayoutProps {
  backendStatus: "checking" | "ok" | "down";
  children: ReactNode;
}

export default function MainLayout({ backendStatus, children }: MainLayoutProps) {
  return (
    <main>
      <header>
        <h1>{env.appTitle}</h1>
        <p>
          Embed a copyright logo in the frequency domain, attack the image (JPEG, crop, noise),
          then extract it again. All algorithm steps run in the Python backend (NumPy / OpenCV);
          this page is the interface.
        </p>
        {backendStatus === "down" && (
          <p className="err banner" data-testid="backend-down">
            Python backend not reachable. Start it with <code>npm run api</code> (port 8000), or
            use <code>npm run dev:all</code>.
          </p>
        )}
      </header>

      {children}

      <footer>
        <h3>Limits (see report)</h3>
        <ul>
          <li>
            Robust to JPEG down to roughly Q≈50 at α=25 and to crops that still hold enough 8×8
            blocks (≥ 4096 blocks ≈ 512×512 px for one copy of every bit). Not to resize, rotation
            or perspective change.
          </li>
          <li>
            Search mode is hypothesis-guided: it needs key and reference logo. Detection threshold =
            mean + 6σ of a wrong-key null distribution measured on the suspect image (mean-centred
            correlation).
          </li>
          <li>
            Uploaded images are kept by the Python backend in a temp folder and deleted after 2
            hours. Transparency is flattened onto white; embed output is always PNG.
          </li>
          <li>
            Research demo. A robust watermark shows origin, not that an image is unmodified.
          </li>
        </ul>
      </footer>
    </main>
  );
}
