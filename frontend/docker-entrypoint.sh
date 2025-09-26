#!/bin/sh

# Generate config.js with environment variables
# In production, use the direct API URL
if [ "${ENVIRONMENT}" = "production" ]; then
  API_URL="${API_URL:-https://cahoots.fly.dev/api}"
  WS_URL="${WS_URL:-wss://cahoots.fly.dev/ws}"
else
  API_URL="${API_URL:-/api}"
  WS_URL="${WS_URL:-/ws}"
fi

cat > /usr/share/nginx/html/config.js <<EOF
window.CAHOOTS_CONFIG = {
  API_URL: '${API_URL}',
  WS_URL: '${WS_URL}',
  ENVIRONMENT: '${ENVIRONMENT:-development}'
};
EOF

# Start nginx
nginx -g 'daemon off;'