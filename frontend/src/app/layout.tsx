import type { Metadata } from "next";

import "./globals.css";

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
      <body>{children}</body>
    </html>
  );
}
