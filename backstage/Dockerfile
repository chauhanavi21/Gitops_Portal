FROM node:18-bookworm-slim AS build

WORKDIR /app
COPY package.json yarn.lock ./
COPY packages/backend/package.json packages/backend/
COPY packages/app/package.json packages/app/
RUN yarn install --frozen-lockfile --network-timeout 300000

COPY . .
RUN yarn build:all

FROM node:18-bookworm-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      python3 \
      build-essential \
      libsqlite3-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/packages/backend/dist ./packages/backend/dist
COPY --from=build /app/packages/app/dist ./packages/app/dist
COPY app-config.yaml app-config.production.yaml ./

ENV NODE_ENV=production

EXPOSE 7007
CMD ["node", "packages/backend/dist/index.cjs.js"]
