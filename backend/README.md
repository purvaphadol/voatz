# Flask Access Control Backend

REST API backend for the Flask Access Control System, built with Flask, SQLAlchemy, and PostgreSQL.

## 🏗️ Architecture

```
backend/
├── app/
│   ├── __init__.py           # Flask app factory
│   ├── models/               # SQLAlchemy models
│   ├── routes/               # API endpoints
│   └── utils/                # Utility functions
├── config/
│   └── config.py             # Configuration settings
├── migrations/               # Database migrations
├── instance/                 # Instance-specific files
├── app.py                    # Application entry point
├── seed_data.py              # Database seeding
└── requirements.txt          # Python dependencies
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Virtual environment (recommended)

### Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables (see Configuration section)
export SECRET_KEY="$(openssl rand -hex 32)"
export JWT_SECRET_KEY="$(openssl rand -hex 32)"
export DATABASE_URL="postgresql://username:password@localhost/database_name"

# Initialize database
flask db upgrade

# Seed initial data
python seed_data.py

# Run the application
python app.py
```

## 🔧 Configuration

### Required Environment Variables

```bash
# Security (Required)
SECRET_KEY=your-super-secret-key-here-minimum-32-characters
JWT_SECRET_KEY=your-jwt-secret-key-here-minimum-32-characters

# Database (Required)
DATABASE_URL=postgresql://username:password@localhost/database_name

# Optional Settings
JWT_EXPIRY_HOURS=2
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
FORCE_HTTPS=false
```

## 📡 API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `GET /api/auth/profile` - Get user profile

### Users
- `GET /api/users` - List company users
- `POST /api/users` - Create user
- `PUT /api/users/{id}` - Update user
- `DELETE /api/users/{id}` - Delete user

### Roles & Permissions
- `GET /api/roles` - List company roles
- `POST /api/roles` - Create role
- `GET /api/permissions/user/{id}` - Get user permissions
- `POST /api/permissions/user/{id}` - Update user permissions

## 🚀 Deployment

### Using Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Health Check
```bash
curl http://localhost:5000/api/health
```

---

**Flask Access Control Backend - Secure, Scalable, Multi-tenant**
