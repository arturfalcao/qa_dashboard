# Multi-stage build for Next.js production optimization
FROM node:18-alpine AS base

# Install pnpm globally
RUN npm install -g pnpm

# ===============================
# Dependencies stage
# ===============================
FROM base AS deps
WORKDIR /app

# Copy workspace and package files from root
COPY package.json pnpm-workspace.yaml ./
COPY packages/shared/package.json ./packages/shared/
COPY apps/web/package.json ./apps/web/

# Install dependencies (including dev deps for building)
COPY pnpm-lock.yaml ./
RUN pnpm install

# ===============================
# Build stage
# ===============================
FROM base AS builder
WORKDIR /app

# Copy node_modules from deps stage
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/packages ./packages
COPY --from=deps /app/apps ./apps

# Copy source code
COPY packages/ ./packages/
COPY apps/web/ ./apps/web/

# Build shared package first
WORKDIR /app/packages/shared
RUN pnpm build

# Build the web application
WORKDIR /app/apps/web
RUN pnpm build

# ===============================
# Production stage
# ===============================
FROM base AS production
WORKDIR /app

# Create non-root user for security
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

# Copy workspace and package files
COPY package.json pnpm-workspace.yaml ./
COPY packages/shared/package.json ./packages/shared/
COPY apps/web/package.json ./apps/web/

# Install only production dependencies
COPY pnpm-lock.yaml ./
RUN pnpm install --prod && \
    pnpm store prune

# Copy built application
COPY --from=builder --chown=nextjs:nodejs /app/packages/shared/dist ./packages/shared/dist
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next ./apps/web/.next
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/public ./apps/web/public

# Copy package.json files for runtime
COPY --chown=nextjs:nodejs packages/shared/package.json ./packages/shared/
COPY --chown=nextjs:nodejs apps/web/package.json ./apps/web/

# Set working directory to web
WORKDIR /app/apps/web

# Switch to non-root user
USER nextjs

# Expose the port that the app runs on
EXPOSE 3000

# Add health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000', (res) => { process.exit(res.statusCode === 200 ? 0 : 1) })" || exit 1

# Start the application
CMD ["pnpm", "start"]
