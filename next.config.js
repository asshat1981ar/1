/** @type {import('next').NextConfig} */
const nextConfig = {
  // Explicitly set the app directory to `app/`
  experimental: {},
  // Allow image domains for client logos, etc.
  images: {
    domains: [],
  },
};

module.exports = nextConfig;
