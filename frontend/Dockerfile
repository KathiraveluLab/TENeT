# Development stage
FROM node:20-alpine AS dev

WORKDIR /app
ARG VITE_API_BASE_URL=/api/cat
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# Production build
FROM node:20-alpine AS build

WORKDIR /app
ARG VITE_API_BASE_URL=/api/cat
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production serve
FROM nginx:alpine AS prod

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
