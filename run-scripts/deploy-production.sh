#!/bin/bash
# Deploy the application to a production server with HTTPS support

# Check if domain is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <domain-name>"
    echo "Example: $0 example.com"
    exit 1
fi

DOMAIN=$1

# Create necessary directories
mkdir -p production-config/certbot/conf
mkdir -p production-config/certbot/www
mkdir -p production-config/nginx

# Update the domain name in nginx configuration
sed "s/your-domain.com/$DOMAIN/g" production-config/nginx/app.conf > production-config/nginx/app.conf.tmp
mv production-config/nginx/app.conf.tmp production-config/nginx/app.conf

# Set environment variables
export ENV_MODE=production
export USE_DOCKER=True

# Change to the project root directory
cd "$(dirname "$0")/.."

# Stop any running containers
docker-compose -f production-config/docker-compose.prod.yml down

# Start the containers
docker-compose -f production-config/docker-compose.prod.yml up -d

# Generate SSL certificate
echo "Waiting for nginx to start..."
sleep 5
docker-compose -f production-config/docker-compose.prod.yml exec certbot certbot --nginx -d $DOMAIN --non-interactive --agree-tos -m your-email@example.com

echo "Deployment completed successfully!"
echo "Your application is now running at https://$DOMAIN"