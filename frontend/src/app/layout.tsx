import type { Metadata } from "next";
import { Noto_Sans_SC, Noto_Serif_SC } from "next/font/google";

import "./globals.css";

const notoSerifSC = Noto_Serif_SC({
  weight: ["400", "600"],
  subsets: ["latin"],
  variable: "--font-narrative",
  display: "swap",
  preload: false,
  adjustFontFallback: false,
});

const notoSansSC = Noto_Sans_SC({
  weight: ["400", "700"],
  subsets: ["latin"],
  variable: "--font-ui",
  display: "swap",
  preload: false,
  adjustFontFallback: false,
});

export const metadata: Metadata = {
  title: "文明灵 CivSim v2",
  description: "文明模拟游戏",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <head>
        {/* 霞鹜文楷：标题/分区标题；CDN 加载，避免本地打包大字体文件 */}
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/npm/lxgw-wenkai-webfont@1/style.css"
        />
      </head>
      <body className={`${notoSerifSC.variable} ${notoSansSC.variable}`}>
        {children}
      </body>
    </html>
  );
}
