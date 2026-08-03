import type { NextConfig } from "next";

const oneYear = 60 * 60 * 24 * 365;

const nextConfig: NextConfig = {
  // next/font 产出的 /_next/static/media/* 默认已带 immutable；
  // 额外为 public/fonts 与静态媒体加固一年缓存，二次访问瞬时命中。
  async headers() {
    return [
      {
        source: "/fonts/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: `public, max-age=${oneYear}, immutable`,
          },
        ],
      },
      {
        source: "/_next/static/media/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: `public, max-age=${oneYear}, immutable`,
          },
        ],
      },
    ];
  },
};

export default nextConfig;
