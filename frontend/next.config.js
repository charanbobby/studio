/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  // typedRoutes rejects dynamic router.push paths; not worth the friction.
  experimental: { typedRoutes: false },
};
module.exports = nextConfig;
