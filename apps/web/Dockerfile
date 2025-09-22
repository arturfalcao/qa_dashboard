FROM node:18-alpine

RUN npm install -g pnpm

WORKDIR /app

# Copy package files
COPY package.json pnpm-workspace.yaml ./
COPY packages/ ./packages/
COPY apps/web/ ./apps/web/

# Install dependencies
RUN pnpm install

# Build shared package first
RUN cd packages/shared && pnpm build

# Build the application
WORKDIR /app/apps/web
RUN pnpm build

EXPOSE 3000

CMD ["pnpm", "start"]