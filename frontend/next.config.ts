import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      { source: "/dashboard", destination: "/manager/home", permanent: false },
      { source: "/customer-info", destination: "/manager/customers", permanent: false },
      { source: "/employee-info", destination: "/manager/employees", permanent: false },
      { source: "/employee-home", destination: "/employee/home", permanent: false },
      { source: "/my-performance", destination: "/employee/performance", permanent: false },
      { source: "/employee", destination: "/employee/home", permanent: false },
      { source: "/manager", destination: "/manager/home", permanent: false },
      { source: "/spatial-analytics", destination: "/manager/spatial-analytics", permanent: false },
      { source: "/settings", destination: "/manager/settings", permanent: false },
      { source: "/alerts", destination: "/manager/alerts", permanent: false },
      { source: "/voice-agent", destination: "/manager/voice-agent", permanent: false },
      { source: "/interactions", destination: "/manager/interactions", permanent: false },
      { source: "/camera-handoff", destination: "/manager/camera-handoff", permanent: false },
      { source: "/compare-people", destination: "/manager/compare-people", permanent: false },
    ];
  },
  outputFileTracingRoot: path.resolve(process.cwd()),
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    // !! WARN !!
    // Dangerously allow production builds to successfully complete even if
    // your project has type errors. We are doing this because Vercel free tier
    // runs out of memory, and we already check types locally.
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
