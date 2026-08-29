import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  typescript: {
    // !! WARN !!
    // Dangerously allow production builds to successfully complete even if
    // your project has type errors. We are doing this because Vercel free tier
    // runs out of memory, and we already check types locally.
    ignoreBuildErrors: true,
  },
};

export default nextConfig;