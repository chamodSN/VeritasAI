FROM node:20-alpine AS builder

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --silent

COPY frontend/ .
RUN npm run build


# Serve with nginx
FROM nginx:alpine AS runtime

COPY --from=builder /app/build /usr/share/nginx/html

# nginx config: proxy /api/* to backend, serve React for everything else
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]