# 1. Upgrade to Node 22 (Vite 8 requirement)
FROM node:22-alpine AS build

WORKDIR /app

# 2. Add build tools for native binaries (needed for Tailwind Oxide)
RUN apk add --no-cache libc6-compat

# 3. Copy package files
COPY package.json package-lock.json ./

# 4. Clean install to ensure correct Linux binaries are downloaded
# We use 'npm ci' for a clean, reliable build in Docker
RUN npm ci

# 5. Copy the rest of your code
COPY . ./

# 6. Build the app (CI=false prevents minor warnings from crashing the build)
RUN CI=false npm run build

# --- STAGE 2: Serve ---
FROM nginx:stable-alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]