# Multi-stage build for production optimization
FROM node:18-alpine AS base

# Install system dependencies required for native modules and Puppeteer
RUN apk add --no-cache \
    chromium \
    nss \
    freetype \
    freetype-dev \
    harfbuzz \
    ca-certificates \
    ttf-freefont \
    python3 \
    make \
    g++

# Tell Puppeteer to use installed Chromium
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium-browser

# Install pnpm globally
RUN npm install -g pnpm

# ===============================
# Dependencies stage
# ===============================
FROM base AS deps
WORKDIR /app

# Copy workspace and package files
COPY package.json pnpm-workspace.yaml ./
COPY packages/shared/package.json ./packages/shared/
COPY apps/api/package.json ./apps/api/

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
COPY apps/api/ ./apps/api/

# Build shared package first
WORKDIR /app/packages/shared
RUN pnpm build

# Build the API
WORKDIR /app/apps/api
RUN pnpm build

# ===============================
# Production stage
# ===============================
FROM base AS production
WORKDIR /app

# Create non-root user for security
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nestjs -u 1001

# Copy workspace and package files
COPY package.json pnpm-workspace.yaml ./
COPY packages/shared/package.json ./packages/shared/
COPY apps/api/package.json ./apps/api/

# Install only production dependencies
COPY pnpm-lock.yaml ./
RUN pnpm install --prod && \
    pnpm store prune

# Copy built application
COPY --from=builder --chown=nestjs:nodejs /app/packages/shared/dist ./packages/shared/dist
COPY --from=builder --chown=nestjs:nodejs /app/apps/api/dist ./apps/api/dist

# Copy package.json files for runtime
COPY --chown=nestjs:nodejs packages/shared/package.json ./packages/shared/
COPY --chown=nestjs:nodejs apps/api/package.json ./apps/api/

# Set working directory to API
WORKDIR /app/apps/api

# Switch to non-root user
USER nestjs

# Expose the port that the app runs on
EXPOSE 3001

# Add health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3001/health', (res) => { process.exit(res.statusCode === 200 ? 0 : 1) })" || exit 1

# Start the application
CMD ["node", "dist/main.js"]