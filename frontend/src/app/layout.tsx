import "./globals.css";
import type { Metadata } from "next";
import { env } from "@/src/@core/config/env";

export const metadata: Metadata = {
  title: env.appTitle,
  description: "Embed and extract robust frequency-domain image watermarks in the browser.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
