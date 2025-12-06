/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    ignoreDuringBuilds: true,
  },
  images: { unoptimized: true },
  output: 'export',
  // async rewrites() { ... } // Rewrites don't work with 'output: export'
};

module.exports = nextConfig;
