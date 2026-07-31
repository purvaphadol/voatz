# Flask Access Control System - Project Structure

## 📁 Directory Structure

```
flask-access-control-system/
├── backend/                           # Flask API Backend
│   ├── app/                          # Flask application package
│   │   ├── __init__.py              # Flask app factory
│   │   ├── models/                  # SQLAlchemy models
│   │   │   ├── __init__.py
│   │   │   ├── audit_log.py         # Audit logging model
│   │   │   ├── base.py              # Base model class
│   │   │   ├── company.py           # Company model
│   │   │   ├── department.py        # Department model
│   │   │   ├── module.py            # Module and actions models
│   │   │   ├── permission.py        # Permission models
│   │   │   ├── role.py              # Role model
│   │   │   └── user.py              # User model
│   │   ├── routes/                  # API endpoints
│   │   │   ├── __init__.py
│   │   │   ├── audit.py             # Audit logs API
│   │   │   ├── auth.py              # Authentication API
│   │   │   ├── companies.py         # Companies API
│   │   │   ├── departments.py       # Departments API
│   │   │   ├── health.py            # Health check API
│   │   │   ├── menu.py              # Menu API
│   │   │   ├── modules.py           # Modules API
│   │   │   ├── module_actions.py    # Module actions API
│   │   │   ├── permissions.py       # Permissions API
│   │   │   ├── permissions_crud.py  # Permission CRUD API
│   │   │   ├── roles.py             # Roles API
│   │   │   ├── users.py             # Users API
│   │   │   └── user_roles.py        # User roles API
│   │   └── utils/                   # Utility functions
│   │       ├── __init__.py
│   │       ├── audit.py             # Audit utilities
│   │       └── otp_utils.py         # OTP utilities
│   ├── config/                      # Configuration files
│   │   └── config.py                # App configuration
│   ├── migrations/                  # Database migrations
│   │   ├── alembic.ini
│   │   ├── env.py
│   │   └── versions/                # Migration versions
│   ├── instance/                    # Instance-specific files
│   │   └── app.db                   # SQLite database (dev)
│   ├── app.py                       # Application entry point
│   ├── seed_data.py                 # Database seeding script
│   ├── check_users.py               # User verification utility
│   ├── requirements.txt             # Python dependencies
│   ├── Dockerfile                   # Backend Docker configuration
│   ├── .env.example                 # Environment variables template
│   └── README.md                    # Backend documentation
│
├── frontend/                        # React Frontend
│   ├── public/                      # Static assets
│   │   ├── index.html               # Main HTML template
│   │   └── favicon.ico              # Favicon
│   ├── src/                         # React source code
│   │   ├── components/              # React components
│   │   │   ├── Audit/
│   │   │   │   └── AuditLogs.js     # Audit logs component
│   │   │   ├── Auth/
│   │   │   │   ├── Login.js         # Login component
│   │   │   │   └── ProtectedRoute.js # Route protection
│   │   │   ├── Companies/
│   │   │   │   └── Companies.js     # Companies management
│   │   │   ├── Dashboard/
│   │   │   │   └── Dashboard.js     # Main dashboard
│   │   │   ├── Departments/
│   │   │   │   └── Departments.js   # Departments management
│   │   │   ├── Layout/
│   │   │   │   └── Layout.js        # Main layout component
│   │   │   ├── Modules/
│   │   │   │   └── Modules.js       # Modules management
│   │   │   ├── Permissions/
│   │   │   │   └── Permissions.js   # Permissions management
│   │   │   ├── Profile/
│   │   │   │   └── Profile.js       # User profile
│   │   │   ├── Roles/
│   │   │   │   └── Roles.js         # Roles management
│   │   │   ├── UserRoles/
│   │   │   │   └── UserRoles.js     # User roles management
│   │   │   └── Users/
│   │   │       └── Users.js         # Users management
│   │   ├── contexts/                # React contexts
│   │   │   ├── AuthContext.js       # Authentication context
│   │   │   └── PermissionContext.js # Permissions context
│   │   ├── services/                # API services
│   │   │   └── api.js               # API client
│   │   ├── App.js                   # Main App component
│   │   ├── App.css                  # App styles
│   │   └── index.js                 # React entry point
│   ├── package.json                 # Node.js dependencies
│   ├── package-lock.json            # Dependency lock file
│   ├── Dockerfile                   # Frontend Docker configuration
│   ├── nginx.conf                   # Nginx configuration
│   └── README.md                    # Frontend documentation
│
├── docs/                            # Documentation
│   ├── SECURITY.md                  # Security guidelines
│   ├── DYNAMIC_PERMISSIONS_GUIDE.md # Permissions guide
│   ├── MODULE_ACTIONS_API.md        # API documentation
│   ├── POSTMAN_COLLECTION_README.md # Postman guide
│   └── REACT_FRONTEND_README.md     # Frontend guide
│
├── docker-compose.yml               # Docker Compose configuration
├── .gitignore                       # Git ignore rules
├── .env.example                     # Environment template
├── setup-dev.sh                     # Development setup script
├── deploy-prod.sh                   # Production deployment script
├── Makefile                         # Development commands
├── README.md                        # Main project documentation
└── PROJECT_STRUCTURE.md             # This file
```

## 🔧 Key Components

### Backend (Flask)
- **Flask Application Factory**: Modular app creation with blueprints
- **SQLAlchemy Models**: Database models with relationships
- **JWT Authentication**: Stateless authentication with role-based access
- **Multi-tenant Architecture**: Company-based data isolation
- **Audit Logging**: Comprehensive activity tracking
- **Permission System**: Role-based + user-specific overrides

### Frontend (React)
- **Material-UI Components**: Professional UI components
- **Context API**: State management for auth and permissions
- **Protected Routes**: Route-level access control
- **DataGrid Integration**: Advanced data tables with filtering
- **Responsive Design**: Mobile-friendly interface
- **Real-time Updates**: Dynamic permission checking

### Infrastructure
- **Docker Support**: Containerized deployment
- **PostgreSQL**: Production-ready database
- **Nginx**: Static file serving and reverse proxy
- **Redis**: Caching and session storage (optional)
- **Health Checks**: Service monitoring endpoints

## 🚀 Deployment Options

### Development
1. **Local Development**: Direct Python/Node.js execution
2. **Docker Development**: `docker-compose up` for full stack

### Production
1. **Docker Compose**: Single-server deployment
2. **Kubernetes**: Scalable container orchestration
3. **Traditional**: Separate server deployment

## 📊 Data Flow

```
User Request → Nginx → React App → API Request → Flask Backend → PostgreSQL
                ↓                                      ↓
            Static Files                         JWT Validation
                                                       ↓
                                                Permission Check
                                                       ↓
                                                Database Query
                                                       ↓
                                                 Audit Logging
```

## 🔐 Security Layers

1. **Network**: HTTPS, CORS, Security Headers
2. **Authentication**: JWT tokens, Password hashing
3. **Authorization**: Role-based + user-specific permissions
4. **Data**: SQL injection protection, Input validation
5. **Audit**: Comprehensive activity logging

## 📈 Scalability Considerations

- **Database**: Read replicas, Connection pooling
- **Backend**: Horizontal scaling with load balancer
- **Frontend**: CDN distribution, Static file caching
- **Caching**: Redis for sessions and frequent queries
- **Monitoring**: Health checks, Logging, Metrics

## 🧪 Testing Strategy

- **Backend**: Unit tests with pytest, Integration tests
- **Frontend**: Component tests with Jest, E2E tests
- **API**: Postman collections, Automated testing
- **Security**: Dependency scanning, Code analysis

---

This structure provides a solid foundation for a scalable, secure, multi-tenant access control system.
