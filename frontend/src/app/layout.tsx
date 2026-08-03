import type { Metadata } from "next";
import localFont from "next/font/local";

import "./globals.css";

/**
 * 自托管完整简体中文字体（WOFF2）。
 * next/font/local 自动注入 preload、hashed 路径与长期缓存。
 * font-display: swap → 先系统 fallback，加载完无缝替换，避免白屏。
 */
const lxgwWenKai = localFont({
  src: "../fonts/LXGWWenKai-Regular.woff2",
  variable: "--font-display-face",
  display: "swap",
  weight: "400",
  style: "normal",
  fallback: ["KaiTi", "STKaiti", "cursive"],
  preload: true,
  adjustFontFallback: false,
});

const notoSerifSC = localFont({
  src: "../fonts/NotoSerifSC-VF.woff2",
  variable: "--font-narrative",
  display: "swap",
  weight: "200 900",
  style: "normal",
  fallback: ["Noto Serif SC", "SimSun", "Songti SC", "serif"],
  preload: true,
  adjustFontFallback: false,
});

const notoSansSC = localFont({
  src: "../fonts/NotoSansSC-VF.woff2",
  variable: "--font-ui",
  display: "swap",
  weight: "100 900",
  style: "normal",
  fallback: ["Noto Sans SC", "PingFang SC", "Microsoft YaHei", "sans-serif"],
  preload: true,
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
    <html
      lang="zh-CN"
      className={`${lxgwWenKai.variable} ${notoSerifSC.variable} ${notoSansSC.variable}`}
    >
      <body>{children}</body>
    </html>
  );
}
