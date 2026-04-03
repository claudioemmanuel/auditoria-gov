import path from "node:path";
import bundleAnalyzer from "@next/bundle-analyzer";

const withBundleAnalyzer = bundleAnalyzer({
  enabled: process.env.ANALYZE === "true",
});

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Dynamic routes require server-side rendering (SSR/ISR).
  // Static export ("output: export") is incompatible with arbitrary IDs —
  // only pre-enumerated params would be generated, causing 404s on real data.
  images: { unoptimized: true },
  trailingSlash: true,
  outputFileTracingRoot: path.join(process.cwd(), "../.."),

  // Security headers are now handled by CloudFront response headers policy
  // (or Caddy in local dev). No server-side rewrites needed — the browser
  // calls NEXT_PUBLIC_API_URL directly.
};

export default withBundleAnalyzer(nextConfig);
