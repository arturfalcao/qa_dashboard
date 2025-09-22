/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ['@qa-dashboard/shared'],
  output: 'standalone',
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