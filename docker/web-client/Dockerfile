FROM node:20-slim

# Install dependencies in a separate directory
WORKDIR /deps
COPY web-client/package*.json ./

# Install dependencies
RUN npm install

# Switch to app directory for runtime
WORKDIR /app

# Create symlink to node_modules
RUN ln -s /deps/node_modules /app/node_modules

EXPOSE 3000

# Use npm to run vite
CMD ["npm", "run", "dev"] 