FROM node:18-alpine as build

WORKDIR /app

# Copy package.json and package-lock.json FIRST for better caching
COPY package*.json ./

# Install dependencies (cached layer if package*.json unchanged)
RUN npm install

# Copy configuration files that rarely change
COPY public/ ./public/
COPY postcss.config.js tailwind.config.js ./

# Copy source code LAST (changes most frequently)
COPY src/ ./src/

# Build the React app
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy the build output to replace the default nginx contents
COPY --from=build /app/build /usr/share/nginx/html

# Copy custom nginx config as template
COPY nginx.conf /etc/nginx/conf.d/default.conf.template

# Copy entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 80

# Use entrypoint to generate config.js with environment variables
ENTRYPOINT ["/docker-entrypoint.sh"]
