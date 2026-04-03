FROM node:22-slim AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

ARG NEXT_PUBLIC_API_URL=http://api:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

# For local dev, the docker-compose.yml overrides CMD with `npm run dev`
# For production, the `out/` directory is deployed to S3 via CI/CD
CMD ["npm", "run", "dev"]
