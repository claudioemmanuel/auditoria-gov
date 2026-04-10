FROM node:22-slim AS deps

WORKDIR /app
RUN useradd -m -u 1001 appuser
COPY package.json package-lock.json* ./
RUN npm ci


FROM deps AS builder

ARG NEXT_PUBLIC_API_URL=http://api:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Explicit copies avoid BuildKit cache conflicts with host node_modules
COPY next.config.mjs postcss.config.mjs tsconfig.json eslint.config.mjs next-env.d.ts ./
COPY src/ src/

RUN npm run build


# ── runtime (minimal production image — no dev deps) ──────────────────────────
FROM node:22-slim AS runtime

WORKDIR /app
RUN useradd -m -u 1001 appuser

COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public 2>/dev/null || true
COPY --from=deps /app/node_modules ./node_modules
COPY package.json ./

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 3000
CMD ["npm", "start"]


FROM deps AS dev

ARG NEXT_PUBLIC_API_URL=http://api:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

COPY next.config.mjs postcss.config.mjs tsconfig.json eslint.config.mjs next-env.d.ts ./
COPY src/ src/

EXPOSE 3000
CMD ["npm", "run", "dev"]
