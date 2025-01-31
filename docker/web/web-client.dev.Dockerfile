FROM node:20-alpine

WORKDIR /app

# Install development dependencies
RUN apk add --no-cache git

# The rest will be mounted from the host
CMD ["npm", "run", "dev"] 