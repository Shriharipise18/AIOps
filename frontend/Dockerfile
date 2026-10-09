# ── Stage 1: install dependencies ────────────────────────────────────────────
FROM node:20-alpine AS dependencies

WORKDIR /app
COPY package*.json ./
RUN npm ci --silent

# ── Stage 2: development runtime ─────────────────────────────────────────────
FROM node:20-alpine AS runtime

WORKDIR /app
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .

EXPOSE 5173

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD wget -qO- http://localhost:5173/ || exit 1

CMD ["npm", "run", "dev"]
