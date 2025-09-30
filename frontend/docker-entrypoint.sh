#!/bin/sh

# Set defaults for environment variables
PORT="${PORT:-80}"
BACKEND_URL="${BACKEND_URL:-https://api.cahoots.cc}"
API_URL="${API_URL:-/api}"
WS_URL="${WS_URL:-/ws}"
ENVIRONMENT="${ENVIRONMENT:-development}"

# Generate config.js with environment variables
cat > /usr/share/nginx/html/config.js <<EOF
window.CAHOOTS_CONFIG = {
  API_URL: '${API_URL}',
  WS_URL: '${WS_URL}',
  ENVIRONMENT: '${ENVIRONMENT}'
};
EOF

# Substitute environment variables in nginx config template
envsubst '${PORT} ${BACKEND_URL}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

# Start nginx
nginx -g 'daemon off;'