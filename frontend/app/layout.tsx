import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "DCT Watermarking Lab",
  description: "Embed and extract robust frequency-domain image watermarks in the browser.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
