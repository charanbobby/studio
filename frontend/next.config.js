const withMDX = require('@next/mdx')();

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  // typedRoutes rejects dynamic router.push paths; not worth the friction.
  experimental: { typedRoutes: false },
  pageExtensions: ['ts', 'tsx', 'mdx'],
};
module.exports = withMDX(nextConfig);
