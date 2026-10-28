import type { Metadata, Viewport } from "next";
import { Geist_Mono, Inter, Lora } from "next/font/google";
import "./globals.css";

import { BRAND } from "@/lib/brand";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin", "latin-ext"],
});

const lora = Lora({
  variable: "--font-lora",
  subsets: ["latin", "latin-ext"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: { default: `${BRAND.name}: ${BRAND.philosophy.replace(/\.$/, "")}`, template: `%s · ${BRAND.name}` },
  description: BRAND.tagline,
  appleWebApp: { capable: true, title: BRAND.name, statusBarStyle: "default" },
};

export const viewport: Viewport = {
  themeColor: BRAND.themeColor,
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${inter.variable} ${lora.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full bg-ivory text-ink">{children}</body>
    </html>
  );
}
