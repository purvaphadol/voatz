# Flask Access Control System with React Frontend

A complete full-stack application featuring a Flask REST API backend with React.js frontend for enterprise-grade access control management.

## 🎯 Project Overview

This is a comprehensive access control system that provides:
- **Multi-tenant Architecture** with company-based data isolation
- **Role-based Access Control (RBAC)** with granular permissions
- **JWT Authentication** with secure token management
- **Dynamic Menu System** based on user permissions
- **Comprehensive Audit Trail** for all user activities
- **Modern React UI** with Material-UI design system

## 🏗️ Architecture

```
flask_full_access_control_project/
├── 📁 app/                          # Flask Backend
│   ├── models/                      # Database models
│   ├── routes/                      # API endpoints
│   └── utils/                       # Utility functions
├── 📁 flask-access-control-frontend/ # React Frontend
│   ├── src/components/              # React components
│   ├── src/contexts/                # State management
│   └── src/services/                # API integration
├── 📁 config/                       # Configuration files
├── 📁 migrations/                   # Database migrations
└── 📄 Flask_Access_Control_APIs.postman_collection.json
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 14+
- PostgreSQL
- Git

### 1. Backend Setup (Flask)

```bash
# Clone and setup virtual environment
git clone <repository>
cd flask_full_access_control_project
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install flask flask-sqlalchemy flask-migrate flask-jwt-extended psycopg2-binary werkzeug

# Configure database
# Update config/config.py with your PostgreSQL credentials

# Run migrations
flask db upgrade

# Seed initial data
python seed_data.py

# Start Flask server
python app.py
```

Backend will run at: `http://localhost:5000`

### 2. Frontend Setup (React)

```bash
# Navigate to frontend directory
cd flask-access-control-frontend

# Install dependencies
npm install

# Start development server
npm start
```

Frontend will run at: `http://localhost:3000`

### 3. Access the Application

1. **Open Browser**: Navigate to `http://localhost:3000`
2. **Login**: Use demo credentials:
   - Email: `john@datagrid.co.in`
   - Password: `admin123`
3. **Explore**: Navigate through the dashboard and modules

## 🔐 Authentication & Security

### JWT Token Flow
1. User submits login credentials
2. Flask validates and returns JWT token
3. React stores token in secure cookies
4. All API requests include Bearer token
5. Flask validates token and permissions

### Permission System
- **Hierarchical Permissions**: Module → Action level control
- **Role-based Assignment**: Users inherit permissions from roles
- **User-specific Overrides**: Individual permission customization
- **Dynamic UI**: Components render based on permissions

## 📊 Database Schema

### Core Tables
- **companies** - Multi-tenant organization data
- **users** - User accounts with company association
- **roles** - Permission groups within companies
- **modules** - System modules (Users, Settings, etc.)
- **module_actions** - Actions per module (view, create, update, delete)
- **user_role_mapping** - User-role assignments
- **role_permission_mapping** - Role-permission assignments
- **user_permission_mapping** - User-specific permission overrides
- **audit_logs** - Complete activity tracking

## 🎨 Frontend Features

### Dashboard
- **Statistics Overview**: User, role, department counts
- **Recent Activities**: Latest audit log entries
- **Permission Summary**: User's available modules
- **System Information**: Company and user details

### User Management
- **Data Grid Interface**: Sortable, filterable user list
- **CRUD Operations**: Create, read, update, delete users
- **Department Assignment**: Link users to departments
- **Permission-based Actions**: Show/hide based on user rights

### Role Management
- **Role Creation**: Define roles with descriptions
- **Permission Assignment**: Link roles to module actions
- **Company Scoping**: Roles isolated by company

### Navigation
- **Dynamic Sidebar**: Permission-based menu items
- **Module Explorer**: Backend-driven module list
- **Responsive Design**: Mobile-friendly interface

## 🔧 API Endpoints

### Authentication
```
POST /api/auth/login          # User authentication
```

### User Management
```
GET    /api/users/            # List users (paginated)
POST   /api/users/            # Create new user
GET    /api/users/{id}        # Get user details
PUT    /api/users/{id}        # Update user
DELETE /api/users/{id}        # Delete user
```

### Role Management
```
GET    /api/roles/            # List roles
POST   /api/roles/            # Create role
PUT    /api/roles/{id}        # Update role
DELETE /api/roles/{id}        # Delete role
```

### Permission System
```
GET    /api/permissions/user              # Current user permissions
GET    /api/permissions/role/{id}         # Role permissions
POST   /api/permissions/role/{id}         # Update role permissions
POST   /api/permissions/user/{id}         # Update user permissions
```

### Dynamic Menu
```
GET    /api/menu/sidebar                  # Sidebar menu with permissions
GET    /api/menu/navigation               # Hierarchical navigation
GET    /api/menu/permissions              # Flat permissions list
```

### Audit System
```
GET    /api/audit/logs                    # Audit log entries
GET    /api/audit/stats                   # Activity statistics
GET    /api/audit/failures                # Failed operations
GET    /api/audit/export                  # Export audit logs
```

## 🧪 Testing

### Backend Testing
```bash
# Test API endpoints with curl
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"john@datagrid.co.in","password":"admin123"}'

# Use Postman collection
# Import Flask_Access_Control_APIs.postman_collection.json
```

### Frontend Testing
```bash
cd flask-access-control-frontend
npm test
```

## 🚀 Deployment

### Backend Deployment
1. **Production Configuration**
   ```python
   # config/config.py
   SQLALCHEMY_DATABASE_URI = "postgresql://user:pass@host/db"
   JWT_SECRET_KEY = "your-secret-key"
   SECRET_KEY = "your-app-secret"
   ```

2. **Database Setup**
   ```bash
   flask db upgrade
   python seed_data.py
   ```

3. **WSGI Server**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

### Frontend Deployment
1. **Build Production**
   ```bash
   cd flask-access-control-frontend
   npm run build
   ```

2. **Serve Static Files**
   - Deploy `build/` folder to web server
   - Configure reverse proxy to Flask API
   - Set up HTTPS certificates

### Environment Variables
```bash
# Backend
export FLASK_ENV=production
export DATABASE_URL=postgresql://...
export JWT_SECRET_KEY=...

# Frontend
export REACT_APP_API_URL=https://api.yourdomain.com/api
```

## 📈 Performance & Scalability

### Backend Optimizations
- **Database Indexing**: Optimized queries with proper indexes
- **Pagination**: All list endpoints support pagination
- **Caching**: JWT token validation caching
- **Connection Pooling**: PostgreSQL connection management

### Frontend Optimizations
- **Code Splitting**: Lazy loading of components
- **Bundle Optimization**: Webpack optimizations
- **API Caching**: Request caching for static data
- **Virtual Scrolling**: Large data set handling

## 🔒 Security Best Practices

### Backend Security
- **JWT Token Expiration**: 24-hour token lifetime
- **Password Hashing**: Werkzeug secure password storage
- **SQL Injection Prevention**: SQLAlchemy ORM protection
- **CORS Configuration**: Proper cross-origin settings

### Frontend Security
- **XSS Prevention**: React's built-in XSS protection
- **CSRF Protection**: SameSite cookie configuration
- **Secure Storage**: JWT tokens in HTTP-only cookies
- **Input Validation**: Client-side validation with server verification

## 🐛 Troubleshooting

### Common Issues

1. **CORS Errors**
   ```python
   # Add to Flask app
   from flask_cors import CORS
   CORS(app)
   ```

2. **JWT Token Issues**
   ```bash
   # Clear browser cookies
   # Check token expiration
   # Verify JWT secret consistency
   ```

3. **Database Connection**
   ```bash
   # Check PostgreSQL service
   sudo systemctl status postgresql
   # Verify connection string
   # Test database connectivity
   ```

4. **React Build Errors**
   ```bash
   # Clear npm cache
   npm cache clean --force
   # Delete node_modules and reinstall
   rm -rf node_modules package-lock.json
   npm install
   ```

## 📚 Documentation

### API Documentation
- **Postman Collection**: Complete API testing suite
- **Endpoint Documentation**: Detailed request/response formats
- **Authentication Guide**: JWT implementation details

### Frontend Documentation
- **Component Documentation**: React component structure
- **State Management**: Context API usage
- **Permission System**: Dynamic UI rendering

## 🤝 Contributing

1. **Fork Repository**
2. **Create Feature Branch**: `git checkout -b feature/new-feature`
3. **Follow Code Standards**: ESLint for frontend, PEP8 for backend
4. **Write Tests**: Unit tests for new functionality
5. **Submit Pull Request**: Detailed description of changes

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

### Getting Help
- **GitHub Issues**: Bug reports and feature requests
- **Documentation**: Check README files in each directory
- **API Testing**: Use provided Postman collection
- **Development**: Enable debug mode for detailed error messages

### Contact
- **Email**: support@example.com
- **Documentation**: [Project Wiki](link)
- **Issues**: [GitHub Issues](link)

---

## 🎉 Success! 

You now have a complete full-stack access control system with:

✅ **Flask REST API** with JWT authentication  
✅ **React Frontend** with Material-UI design  
✅ **Role-based Permissions** with dynamic UI  
✅ **Multi-tenant Architecture** for enterprise use  
✅ **Comprehensive Audit Trail** for compliance  
✅ **Production-ready Deployment** configuration  

**Happy coding! 🚀** 