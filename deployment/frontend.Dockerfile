FROM node:24-alpine AS build
WORKDIR /app
ARG APP=storefront
ENV NEXT_TELEMETRY_DISABLED=1
COPY package*.json ./
COPY apps/storefront/package.json apps/storefront/package.json
COPY apps/admin/package.json apps/admin/package.json
RUN npm ci --no-audit --no-fund
COPY apps ./apps
COPY packages ./packages
RUN npm run build --workspace @retail/${APP}

FROM node:24-alpine AS runtime
WORKDIR /app
ARG APP=storefront
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
RUN addgroup -g 10001 retail && adduser -D -u 10001 -G retail retail
COPY --from=build --chown=retail:retail /app/apps/${APP}/.next/standalone ./
COPY --from=build --chown=retail:retail /app/apps/${APP}/.next/static ./apps/${APP}/.next/static
USER retail
ENV APP_NAME=${APP}
EXPOSE 3000
CMD ["sh","-c","node apps/${APP_NAME}/server.js"]

