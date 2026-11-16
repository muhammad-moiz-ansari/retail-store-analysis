import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    name: "RetailPulse",
    short_name: "RetailPulse",
    description: "Store analytics and employee workflows",
    start_url: "/",
    scope: "/",
    display: "standalone",
    background_color: "#FAF8F2",
    theme_color: "#FAF8F2",
    icons: [
      { src: "/pwa-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/pwa-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/pwa-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
