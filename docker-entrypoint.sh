#!/bin/bash
set -e

# Default environment to development if not specified
ENV_MODE=${ENV_MODE:-development}

# Set default port based on environment
if [ "$ENV_MODE" = "development" ]; then
    PORT=${PORT:-5000}
else
    PORT=${PORT:-8080}
fi

echo "Starting application in $ENV_MODE mode on port $PORT"

# Run the application with Gunicorn
cd /app/src
exec gunicorn \
    -w 4 \
    --preload \
    --timeout 90 \
    -b "0.0.0.0:$PORT" \
    --worker-class gevent \
    app:app