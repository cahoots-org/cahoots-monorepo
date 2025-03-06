# Simple Nginx image to serve static files
FROM nginx:alpine

# Copy the static files to nginx
COPY web-client/dist /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]