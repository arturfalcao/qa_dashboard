# This is a base Dockerfile that can be used by both apps
FROM node:18-alpine

RUN npm install -g pnpm

WORKDIR /app

# Copy package files
COPY package.json pnpm-workspace.yaml ./
COPY packages/ ./packages/

# This will be overridden by the specific app Dockerfiles
COPY apps/ ./apps/

# Install dependencies
RUN pnpm install

# Default command (will be overridden)
CMD ["echo", "Please specify a command"]