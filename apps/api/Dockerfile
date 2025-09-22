FROM node:18-alpine

RUN npm install -g pnpm

WORKDIR /app

# Copy package files
COPY package.json pnpm-workspace.yaml ./
COPY packages/ ./packages/
COPY apps/api/ ./apps/api/

# Install dependencies
RUN pnpm install

# Build shared package first
RUN cd packages/shared && pnpm build

# Build the application
WORKDIR /app/apps/api
RUN pnpm build

EXPOSE 3001

CMD ["pnpm", "start:prod"]