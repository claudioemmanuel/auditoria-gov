import bundleAnalyzer from "@next/bundle-analyzer";

const withBundleAnalyzer = bundleAnalyzer({
  enabled: process.env.ANALYZE === "true",
});

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: process.env.NODE_ENV === "production" ? "export" : undefined,
  images: { unoptimized: true },
  trailingSlash: true,

  // Security headers are now handled by CloudFront response headers policy
  // (or Caddy in local dev). No server-side rewrites needed — the browser
  // calls NEXT_PUBLIC_API_URL directly.
};

export default withBundleAnalyzer(nextConfig);
