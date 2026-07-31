Great! Now let me guide you through setting up the Flask Access Control System using Docker. This is much easier and more consistent across different environments.

## 🐳 Docker Setup Guide - Flask Access Control System

### Prerequisites

Make sure you have Docker and Docker Compose installed:

```bash
# Check if Docker is installed
docker --version

# Check if Docker Compose is installed
docker-compose --version

# If not installed, install Docker (Ubuntu/Debian)
sudo apt update
sudo apt install docker.io docker-compose

# Add your user to docker group (to run without sudo)
sudo usermod -aG docker $USER
# Log out and log back in for this to take effect
```

### 📁 Step 1: Navigate to Project Directory

```bash
cd /var/www/html/Python/flask-access-control-system
```

### 🔧 Step 2: Environment Configuration

The Docker setup uses environment variables defined in the `docker-compose.yml` file, but you can also create a `.env` file for Docker Compose:

```bash
# Create .env file for Docker Compose (optional but recommended)
cat > .env << 'EOF'
# Database Configuration
POSTGRES_DB=flask_access_control
POSTGRES_USER=flask_user
POSTGRES_PASSWORD=secure_password_change_in_production

# Flask Backend Configuration
SECRET_KEY=your-super-secret-key-here-minimum-32-characters-long-change-this
JWT_SECRET_KEY=your-jwt-secret-key-here-minimum-32-characters-long-change-this
DATABASE_URL=postgresql://flask_user:secure_password_change_in_production@postgres:5432/flask_access_control
CORS_ORIGINS=http://localhost:3000,http://localhost:80
FLASK_ENV=production

# Optional Redis Configuration
REDIS_URL=redis://redis:6379/0
EOF
```

### 🏗️ Step 3: Build and Start Services

#### Option A: Quick Start (Recommended)
```bash
# Build and start all services in detached mode
docker-compose up --build -d

# Check if services are running
docker-compose ps
```

#### Option B: Step-by-Step Build
```bash
# Build images first
docker-compose build

# Start services
docker-compose up -d

# Or start with logs visible (for debugging)
docker-compose up --build
```

### 📊 Step 4: Initialize Database

After the services are running, initialize the database:

```bash
# Wait for PostgreSQL to be ready (about 30 seconds)
sleep 30

# Run database migrations
docker-compose exec backend flask db upgrade

# Seed initial data
docker-compose exec backend python seed_data.py
```

### 🔍 Step 5: Verify Setup

Check if everything is working:

```bash
# Check service status
docker-compose ps

# Check logs
docker-compose logs backend
docker-compose logs frontend
docker-compose logs postgres

# Test backend health
curl http://localhost:5000/api/health

# Test frontend
curl http://localhost/health
```

### 🌐 Step 6: Access the Application

- **Frontend**: http://localhost (port 80)
- **Backend API**: http://localhost:5000
- **Default Login**: rushiraj@datagrid.co.in / admin123

### 🛠️ Step 7: Common Docker Commands

#### Service Management
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart services
docker-compose restart

# Restart specific service
docker-compose restart backend

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres

# Follow all logs
docker-compose logs -f
```

#### Database Operations
```bash
# Access PostgreSQL database
docker-compose exec postgres psql -U flask_user -d flask_access_control

# Run database migrations
docker-compose exec backend flask db migrate -m "Description"
docker-compose exec backend flask db upgrade

# Seed data
docker-compose exec backend python seed_data.py

# Check users
docker-compose exec backend python check_users.py
```

#### Development Commands
```bash
# Access backend container shell
docker-compose exec backend bash

# Access frontend container shell
docker-compose exec frontend sh

# Run backend tests
docker-compose exec backend python -m pytest

# Install new Python package
docker-compose exec backend pip install new-package
docker-compose exec backend pip freeze > requirements.txt
```

### 🔧 Step 8: Development with Docker

For development, you might want to mount your code as volumes for live reloading:

Create a `docker-compose.dev.yml` file:

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    volumes:
      - ./backend:/app
    environment:
      - FLASK_ENV=development
      - FLASK_DEBUG=true
    ports:
      - "5000:5000"
    command: ["python", "app.py"]

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev  # We'll create this
    volumes:
      - ./frontend/src:/app/src
      - ./frontend/public:/app/public
    ports:
      - "3000:3000"
    command: ["npm", "start"]
```

Create development Dockerfile for frontend:

```bash
cat > frontend/Dockerfile.dev << 'EOF'
FROM node:16-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000

CMD ["npm", "start"]
EOF
```

Run development environment:
```bash
# Use development compose file
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

### 🚀 Step 9: Production Deployment

For production, update the environment variables:

```bash
# Create production environment file
cat > .env.prod << 'EOF'
# Database Configuration
POSTGRES_DB=flask_access_control_prod
POSTGRES_USER=flask_user_prod
POSTGRES_PASSWORD=very_secure_password_change_this

# Flask Backend Configuration
SECRET_KEY=production-secret-key-minimum-32-characters-very-secure
JWT_SECRET_KEY=production-jwt-secret-key-minimum-32-characters-very-secure
DATABASE_URL=postgresql://flask_user_prod:very_secure_password_change_this@postgres:5432/flask_access_control_prod
CORS_ORIGINS=https://yourdomain.com
FLASK_ENV=production
FORCE_HTTPS=true

# Security
JWT_EXPIRY_HOURS=1
EOF

# Deploy with production environment
docker-compose --env-file .env.prod up -d --build
```

### 🔒 Step 10: Security Considerations

For production deployment:

1. **Change default passwords**:
   ```bash
   # Generate secure passwords
   openssl rand -hex 32  # For SECRET_KEY
   openssl rand -hex 32  # For JWT_SECRET_KEY
   openssl rand -base64 32  # For database password
   ```

2. **Use Docker secrets** (for Docker Swarm):
   ```yaml
   secrets:
     db_password:
       file: ./secrets/db_password.txt
     jwt_secret:
       file: ./secrets/jwt_secret.txt
   ```

3. **Enable HTTPS** with reverse proxy (Nginx/Traefik)

4. **Set up monitoring** and health checks

### 🧪 Step 11: Troubleshooting

#### Common Issues and Solutions:

1. **Port already in use**:
   ```bash
   # Find what's using the port
   sudo lsof -i :5000
   sudo lsof -i :80
   
   # Stop conflicting services or change ports in docker-compose.yml
   ```

2. **Database connection issues**:
   ```bash
   # Check PostgreSQL logs
   docker-compose logs postgres
   
   # Verify database is running
   docker-compose exec postgres pg_isready -U flask_user
   ```

3. **Backend not starting**:
   ```bash
   # Check backend logs
   docker-compose logs backend
   
   # Access backend container
   docker-compose exec backend bash
   ```

4. **Frontend build issues**:
   ```bash
   # Check frontend logs
   docker-compose logs frontend
   
   # Rebuild frontend
   docker-compose build frontend
   ```

5. **Permission issues**:
   ```bash
   # Fix file permissions
   sudo chown -R $USER:$USER .
   ```

### 📊 Step 12: Monitoring and Maintenance

#### Health Checks
```bash
# Check all services health
curl http://localhost:5000/api/health/detailed
curl http://localhost/health

# Monitor resource usage
docker stats
```

#### Backup and Restore
```bash
# Backup database
docker-compose exec postgres pg_dump -U flask_user flask_access_control > backup.sql

# Restore database
docker-compose exec -T postgres psql -U flask_user flask_access_control < backup.sql
```

#### Updates
```bash
# Pull latest images
docker-compose pull

# Rebuild and restart
docker-compose up --build -d

# Clean up old images
docker system prune -f
```

### ✅ Complete Docker Setup Summary

Here's the complete setup in one go:

```bash
# 1. Navigate to project
cd /var/www/html/Python/flask-access-control-system

# 2. Create environment file
cat > .env << 'EOF'
POSTGRES_DB=flask_access_control
POSTGRES_USER=flask_user
POSTGRES_PASSWORD=secure_password_change_in_production
SECRET_KEY=your-super-secret-key-here-minimum-32-characters-long
JWT_SECRET_KEY=your-jwt-secret-key-here-minimum-32-characters-long
DATABASE_URL=postgresql://flask_user:secure_password_change_in_production@postgres:5432/flask_access_control
CORS_ORIGINS=http://localhost:3000,http://localhost:80
FLASK_ENV=production
EOF

# 3. Build and start services
docker-compose up --build -d

# 4. Wait for services to be ready
sleep 30

# 5. Initialize database
docker-compose exec backend flask db upgrade
docker-compose exec backend python seed_data.py

# 6. Check status
docker-compose ps

# 7. Test application
curl http://localhost:5000/api/health
echo "Frontend: http://localhost"
echo "Backend: http://localhost:5000"
echo "Login: rushiraj@datagrid.co.in / admin123"
```

### 🎉 That's it!

Your Flask Access Control System is now running with Docker! The benefits include:

- ✅ **Consistent Environment**: Same setup across development, staging, and production
- ✅ **Easy Deployment**: Single command deployment
- ✅ **Isolated Services**: Each component runs in its own container
- ✅ **Scalability**: Easy to scale individual services
- ✅ **Backup & Recovery**: Simple database backup and restore
- ✅ **Health Monitoring**: Built-in health checks
- ✅ **Security**: Isolated network and proper secrets management

The application will be available at:
- **Frontend**: http://localhost
- **Backend API**: http://localhost:5000
- **Login**: rushiraj@datagrid.co.in / admin123
