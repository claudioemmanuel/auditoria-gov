FROM node:22-slim AS deps

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci


FROM deps AS builder

ARG NEXT_PUBLIC_API_URL=http://api:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Explicit copies avoid BuildKit cache conflicts with host node_modules
COPY next.config.mjs postcss.config.mjs tsconfig.json eslint.config.mjs next-env.d.ts ./
COPY src/ src/

RUN npm run build


FROM deps AS dev

ARG NEXT_PUBLIC_API_URL=http://api:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

COPY next.config.mjs postcss.config.mjs tsconfig.json eslint.config.mjs next-env.d.ts ./
COPY src/ src/

EXPOSE 3000
CMD ["npm", "run", "dev"]
