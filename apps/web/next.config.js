/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ['@qa-dashboard/shared'],
  output: 'standalone',
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'images.unsplash.com',
      },
      {
        protocol: 'https',
        hostname: 'placehold.co',
      },
      {
        protocol: 'https',
        hostname: '*.digitaloceanspaces.com',
      },
      {
        protocol: 'https',
        hostname: 'lon1.digitaloceanspaces.com',
      },
    ],
    unoptimized: false,
  },
  webpack: (config, { isServer }) => {
    // Handle TypeScript files in workspace packages
    config.resolve.extensionAlias = {
      '.js': ['.js', '.ts', '.tsx'],
      '.jsx': ['.jsx', '.tsx'],
    }

    return config
  },
}

module.exports = nextConfig