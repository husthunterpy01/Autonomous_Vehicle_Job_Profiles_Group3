FROM node:22-slim AS build

WORKDIR /app

# Install deps first so this layer is cached unless the lockfile changes
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
# next.config.ts sets output: "export", so this produces static files in ./out
RUN npm run build

FROM node:22-slim

WORKDIR /app
RUN npm install -g serve@14

COPY --from=build /app/out ./out

EXPOSE 3000

CMD ["serve", "-s", "out", "-l", "3000"]
