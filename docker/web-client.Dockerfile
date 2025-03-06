# Stage 1: Build the application
FROM node:18 as builder

WORKDIR /app

# Copy package files
COPY web-client/package*.json ./

# Install dependencies
RUN npm install

# Copy source files
COPY web-client/ .

# Build the application
RUN npm run build

# Stage 2: Serve the application
FROM nginx:alpine

# Copy the built files from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]