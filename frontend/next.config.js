const { withSentryConfig } = require("@sentry/nextjs");

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",

  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "lh3.googleusercontent.com",
      },
    ],
  },

  compress: true,
  poweredByHeader: false,
  reactStrictMode: true,
  productionBrowserSourceMaps: false,

  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "SAMEORIGIN" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-XSS-Protection", value: "1; mode=block" },
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline' https://*.paddle.com https://*.googletagmanager.com https://*.google-analytics.com",
              "style-src 'self' 'unsafe-inline' https://*.paddle.com",
              "img-src 'self' data: blob: https://lh3.googleusercontent.com https://*.paddle.com https://*.google-analytics.com https://*.googletagmanager.com",
              "font-src 'self' https://*.paddle.com",
              "connect-src 'self' https://*.paddle.com https://*.google-analytics.com https://*.googletagmanager.com",
              "frame-src https://*.paddle.com",
              "base-uri 'self'",
            ].join("; "),
          },
        ],
      },
    ];
  },
};

module.exports = withSentryConfig(nextConfig, {
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  silent: true,
  widenClientFileUpload: true,
  tunnelRoute: "/monitoring",
});
