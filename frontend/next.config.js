/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.API_URL || 'http://backend:8484'}/:path*`,
      },
      {
        source: '/open/:path*',
        destination: `${process.env.API_URL || 'http://backend:8484'}/open/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
