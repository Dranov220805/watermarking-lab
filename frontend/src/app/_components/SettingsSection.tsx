"use client";

import type { WatermarkMethod } from "@/src/services/watermark-service/operations/models/input.model";

interface SettingsSectionProps {
  secretKey: string;
  alpha: number;
  method: WatermarkMethod;
  onSecretKeyChange: (value: string) => void;
  onAlphaChange: (value: number) => void;
  onMethodChange: (value: WatermarkMethod) => void;
}

export default function SettingsSection({
  secretKey,
  alpha,
  method,
  onSecretKeyChange,
  onAlphaChange,
  onMethodChange,
}: SettingsSectionProps) {
  return (
    <section className="card" id="settings">
      <h2>
        Settings <small>(shared by embed and extract)</small>
      </h2>
      <div className="grid3">
        <label>
          Secret key
          <input
            value={secretKey}
            onChange={(e) => onSecretKeyChange(e.target.value)}
            data-testid="key"
          />
        </label>
        <label>
          Strength α = {alpha}
          <input
            type="range"
            min={10}
            max={60}
            value={alpha}
            onChange={(e) => onAlphaChange(+e.target.value)}
            data-testid="alpha"
          />
          <small>Higher: survives stronger JPEG, but lower image quality.</small>
        </label>
        <label>
          Method
          <select
            value={method}
            onChange={(e) => onMethodChange(e.target.value as WatermarkMethod)}
            data-testid="method"
          >
            <option value="dct">DCT mid-frequency (robust)</option>
            <option value="lsb">LSB spatial (baseline, fragile)</option>
          </select>
          <small>Use LSB to see why the spatial domain fails under JPEG.</small>
        </label>
      </div>
    </section>
  );
}
