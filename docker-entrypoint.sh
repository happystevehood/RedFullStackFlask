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

# Change to the project root directory
cd "$(dirname "$0")/src"

# Run Gunicorn using the Python config file.
exec gunicorn --config "$(dirname "$0")/src/rl/rl_gunicorn.py" app:app
#exec gunicorn --config src.rl.gunicorn_conf src.app:app
