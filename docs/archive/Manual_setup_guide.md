I'll provide you with detailed manual setup steps for the Flask Access Control System without using Docker.

## 🚀 Manual Setup Guide - Flask Access Control System

### Prerequisites

Before starting, ensure you have:
- **Python 3.8+** installed
- **Node.js 16+** and npm installed
- **PostgreSQL 12+** installed and running
- **Git** (optional, for version control)

### 📊 Step 1: Database Setup

First, set up PostgreSQL database:

```bash
# Connect to PostgreSQL as superuser
sudo -u postgres psql

# Create database and user
CREATE DATABASE flask_access_control;
CREATE USER flask_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE flask_access_control TO flask_user;

# Exit PostgreSQL
\q
```

Test the database connection:
```bash
psql -h localhost -U flask_user -d flask_access_control
# Enter password when prompted
# If successful, you'll see the PostgreSQL prompt
\q
```

### 🔧 Step 2: Backend Setup

Navigate to your project directory and set up the backend:

```bash
# Navigate to backend directory
cd /var/www/html/Python/flask-access-control-system/backend

# Create Python virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
pip install -r requirements.txt
```

### 🔐 Step 3: Environment Configuration

Create environment file for backend:

```bash
# Copy environment template
cp .env.example .env

# Edit the .env file with your actual values
nano .env  # or use your preferred editor
```

Update the `.env` file with your actual values:

```bash
# Security Configuration (REQUIRED)
SECRET_KEY=your-super-secret-key-here-minimum-32-characters-long
JWT_SECRET_KEY=your-jwt-secret-key-here-minimum-32-characters-long

# Database Configuration (REQUIRED)
DATABASE_URL=postgresql://flask_user:your_secure_password@localhost:5432/flask_access_control

# Optional Settings
JWT_EXPIRY_HOURS=2
CORS_ORIGINS=http://localhost:3000
FORCE_HTTPS=false
FLASK_ENV=development
FLASK_DEBUG=true
```

**Generate secure keys:**
```bash
# Generate SECRET_KEY
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"

# Generate JWT_SECRET_KEY
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_hex(32))"
```

### 📊 Step 4: Database Migration and Seeding

Initialize and set up the database:

```bash
# Make sure you're in the backend directory with venv activated
cd /var/www/html/Python/flask-access-control-system/backend
source venv/bin/activate

# Set Flask app environment variable
export FLASK_APP=app.py

# Initialize database migrations (if not already done)
flask db init  # Skip if migrations folder already exists

# Create migration files
flask db migrate -m "Initial migration"

# Apply migrations to database
flask db upgrade

# Seed initial data (creates admin user, roles, permissions, etc.)
python seed_data.py
```

### 🧪 Step 5: Test Backend

Test if the backend is working:

```bash
# Start the Flask development server
python app.py
```

You should see output like:
```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

Test the API in another terminal:
```bash
# Test health check
curl http://localhost:5000/api/health

# Test login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "rushiraj@datagrid.co.in", "password": "admin123"}'
```

### 🎨 Step 6: Frontend Setup

Open a new terminal and set up the frontend:

```bash
# Navigate to frontend directory
cd /var/www/html/Python/flask-access-control-system/frontend

# Install Node.js dependencies
npm install

# Start the React development server
npm start
```

The frontend should automatically open in your browser at `http://localhost:3000`.

### 🔍 Step 7: Verify Complete Setup

1. **Backend Health Check:**
   - Visit: `http://localhost:5000/api/health`
   - Should return: `{"status": "ok", "timestamp": "...", "service": "flask-access-control-backend"}`

2. **Frontend Access:**
   - Visit: `http://localhost:3000`
   - Should show the login page

3. **Login Test:**
   - Email: `rushiraj@datagrid.co.in`
   - Password: `admin123`
   - Should successfully log in and show the dashboard

### 🔄 Step 8: Development Workflow

For daily development, use these commands:

**Start Backend:**
```bash
cd /var/www/html/Python/flask-access-control-system/backend
source venv/bin/activate
python app.py
```

**Start Frontend (in another terminal):**
```bash
cd /var/www/html/Python/flask-access-control-system/frontend
npm start
```

### 🛠️ Step 9: Common Development Tasks

**Database Operations:**
```bash
cd backend
source venv/bin/activate

# Create new migration after model changes
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Reset database (development only)
flask db downgrade
python seed_data.py
```

**Adding New Dependencies:**
```bash
# Backend
cd backend
source venv/bin/activate
pip install new-package
pip freeze > requirements.txt

# Frontend
cd frontend
npm install new-package
```

**Check User Data:**
```bash
cd backend
source venv/bin/activate
python check_users.py
```

### 🚨 Troubleshooting

**Common Issues and Solutions:**

1. **Database Connection Error:**
   ```bash
   # Check PostgreSQL is running
   sudo systemctl status postgresql
   
   # Start PostgreSQL if not running
   sudo systemctl start postgresql
   
   # Test connection
   psql -h localhost -U flask_user -d flask_access_control
   ```

2. **Python Module Not Found:**
   ```bash
   # Make sure virtual environment is activated
   source backend/venv/bin/activate
   
   # Reinstall requirements
   pip install -r backend/requirements.txt
   ```

3. **Node Modules Error:**
   ```bash
   # Clear npm cache and reinstall
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   ```

4. **Port Already in Use:**
   ```bash
   # Find process using port 5000
   lsof -i :5000
   
   # Kill the process (replace PID with actual process ID)
   kill -9 PID
   
   # Or use different port
   export FLASK_RUN_PORT=5001
   ```

5. **CORS Issues:**
   - Make sure `CORS_ORIGINS=http://localhost:3000` is set in backend `.env`
   - Restart the backend server after changing environment variables

### 📊 Step 10: Production Considerations

For production deployment:

1. **Environment Variables:**
   ```bash
   export FLASK_ENV=production
   export FLASK_DEBUG=false
   export SECRET_KEY="your-production-secret-key"
   export DATABASE_URL="postgresql://prod_user:secure_pass@prod-db-server/prod_db"
   ```

2. **Use Production Server:**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

3. **Build Frontend for Production:**
   ```bash
   cd frontend
   npm run build
   ```

4. **Serve Frontend with Nginx:**
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;
       
       location / {
           root /path/to/frontend/build;
           try_files $uri /index.html;
       }
       
       location /api {
           proxy_pass http://localhost:5000;
       }
   }
   ```

### ✅ Setup Complete!

Your Flask Access Control System is now running manually without Docker:

- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:5000  
- **Default Login**: rushiraj@datagrid.co.in / admin123

The system includes:
- ✅ Multi-tenant company management
- ✅ Role-based access control
- ✅ User-specific permission overrides
- ✅ Complete CRUD operations for all entities
- ✅ Audit logging
- ✅ Professional React UI with Material-UI

You can now start developing and customizing the system according to your needs!
