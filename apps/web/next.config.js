const createNextIntlPlugin = require("next-intl/plugin");
const withNextIntl = createNextIntlPlugin("./i18n/request.ts");

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `http://127.0.0.1:${process.env.API_PORT || 8999}/api/:path*`,
      },
      {
        source: '/health',
        destination: `http://127.0.0.1:${process.env.API_PORT || 8999}/health`,
      },
    ];
  },
};

module.exports = withNextIntl(nextConfig);
