"use client";

import { useEffect, useState } from "react";
import { DEFAULT_ALPHA, DEFAULT_METHOD, DEFAULT_SECRET_KEY } from "@/src/@core/const";
import { scrollToElement } from "@/src/@core/utils/file";
import MainLayout from "@/src/layouts/MainLayout";
import type { ImageAssetOutputModel } from "@/src/services/watermark-service/image/models/output.model";
import type { WatermarkMethod } from "@/src/services/watermark-service/operations/models/input.model";
import { watermarkService } from "@/src/services/watermark-service/watermark.service";
import AttackLabSection from "./_components/AttackLabSection";
import EmbedSection from "./_components/EmbedSection";
import ExtractSection from "./_components/ExtractSection";
import SettingsSection from "./_components/SettingsSection";

export default function HomePage() {
  const [backendStatus, setBackendStatus] = useState<"checking" | "ok" | "down">("checking");
  const [secretKey, setSecretKey] = useState(DEFAULT_SECRET_KEY);
  const [alpha, setAlpha] = useState(DEFAULT_ALPHA);
  const [method, setMethod] = useState<WatermarkMethod>(DEFAULT_METHOD);

  const [labSource, setLabSource] = useState<ImageAssetOutputModel | null>(null);
  const [extractSource, setExtractSource] = useState<ImageAssetOutputModel | null>(null);

  useEffect(() => {
    watermarkService.healthService
      .checkHealthAsync()
      .then(() => setBackendStatus("ok"))
      .catch(() => setBackendStatus("down"));
  }, []);

  function handleSendToLab(asset: ImageAssetOutputModel) {
    setLabSource(asset);
    scrollToElement("lab");
  }

  function handleSendToExtract(asset: ImageAssetOutputModel) {
    setExtractSource(asset);
    scrollToElement("extract");
  }

  return (
    <MainLayout backendStatus={backendStatus}>
      <SettingsSection
        secretKey={secretKey}
        alpha={alpha}
        method={method}
        onSecretKeyChange={setSecretKey}
        onAlphaChange={setAlpha}
        onMethodChange={setMethod}
      />
      <EmbedSection
        secretKey={secretKey}
        alpha={alpha}
        method={method}
        onSendToLab={handleSendToLab}
        onSendToExtract={handleSendToExtract}
      />
      <AttackLabSection
        sourceImage={labSource}
        onSourceImageChange={setLabSource}
        onSendToExtract={handleSendToExtract}
      />
      <ExtractSection
        sourceImage={extractSource}
        secretKey={secretKey}
        alpha={alpha}
        method={method}
        onSourceImageChange={setExtractSource}
      />
    </MainLayout>
  );
}
