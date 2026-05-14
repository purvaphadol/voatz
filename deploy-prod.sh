#!/bin/bash

# Flask Access Control System - Production Deployment Script

set -e

echo "🚀 Deploying Flask Access Control System to Production"
echo "======================================================"

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Check for required environment variables
if [ -z "$SECRET_KEY" ] || [ -z "$JWT_SECRET_KEY" ] || [ -z "$DATABASE_URL" ]; then
    echo "❌ Error: Required environment variables not set!"
    echo "Please set: SECRET_KEY, JWT_SECRET_KEY, DATABASE_URL"
    exit 1
fi

echo "🔧 Building and deploying with Docker Compose..."

# Pull latest images
docker-compose pull

# Build and start services
docker-compose up --build -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 30

# Check service health
echo "🏥 Checking service health..."
docker-compose ps

# Run database migrations
echo "📊 Running database migrations..."
docker-compose exec backend flask db upgrade

# Seed initial data (if needed)
read -p "Do you want to seed initial data? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🌱 Seeding initial data..."
    docker-compose exec backend python seed_data.py
fi

echo "✅ Deployment completed!"
echo ""
echo "🌐 Application URLs:"
echo "- Frontend: http://localhost"
echo "- Backend API: http://localhost:5000"
echo "- Health Check: http://localhost:5000/api/health"
echo ""
echo "📊 Service Status:"
docker-compose ps
echo ""
echo "📝 Logs:"
echo "docker-compose logs -f [service_name]"
echo ""
echo "🛑 To stop:"
echo "docker-compose down"
