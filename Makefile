# Flask Access Control System - Makefile

.PHONY: help setup dev prod test clean build deploy

# Default target
help:
	@echo "Flask Access Control System - Available Commands"
	@echo "==============================================="
	@echo "setup     - Set up development environment"
	@echo "dev       - Start development servers"
	@echo "prod      - Deploy to production with Docker"
	@echo "test      - Run tests"
	@echo "clean     - Clean up temporary files"
	@echo "build     - Build Docker images"
	@echo "deploy    - Deploy to production"
	@echo "logs      - Show Docker logs"
	@echo "stop      - Stop all services"
	@echo "restart   - Restart all services"

# Development setup
setup:
	@echo "Setting up development environment..."
	./setup-dev.sh

# Start development servers
dev:
	@echo "Starting development servers..."
	@echo "Starting backend in background..."
	cd backend && source venv/bin/activate && python app.py &
	@echo "Starting frontend..."
	cd frontend && npm start

# Production deployment
prod:
	@echo "Deploying to production..."
	./deploy-prod.sh

# Build Docker images
build:
	@echo "Building Docker images..."
	docker-compose build

# Deploy with Docker
deploy:
	@echo "Deploying with Docker Compose..."
	docker-compose up -d --build

# Show logs
logs:
	docker-compose logs -f

# Stop services
stop:
	docker-compose down

# Restart services
restart:
	docker-compose restart

# Run tests
test:
	@echo "Running backend tests..."
	cd backend && source venv/bin/activate && python -m pytest
	@echo "Running frontend tests..."
	cd frontend && npm test

# Clean up
clean:
	@echo "Cleaning up temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name "*~" -delete 2>/dev/null || true
	docker system prune -f

# Database operations
db-migrate:
	@echo "Creating database migration..."
	cd backend && source venv/bin/activate && flask db migrate

db-upgrade:
	@echo "Applying database migrations..."
	cd backend && source venv/bin/activate && flask db upgrade

db-seed:
	@echo "Seeding database..."
	cd backend && source venv/bin/activate && python seed_data.py

# Security
security-check:
	@echo "Running security checks..."
	cd backend && source venv/bin/activate && pip install safety bandit
	cd backend && source venv/bin/activate && safety check
	cd backend && source venv/bin/activate && bandit -r app/
	cd frontend && npm audit

# Update dependencies
update-deps:
	@echo "Updating dependencies..."
	cd backend && source venv/bin/activate && pip install --upgrade -r requirements.txt
	cd frontend && npm update
