# Project Folder Structure & Directory Map

This document outlines the organization and directory structure of the Voatz multi-tenant platform repository.

---

## Root Directory Overview

```
voatz/
├── backend/                  # Flask REST API Backend
├── docs/                     # Centralized System Documentation
│   └── archive/              # Legacy specification & enhancement READMEs
├── frontend/                 # React dynamic single-page web application
└── README.md                 # Primary project overview
```

---

## Backend Directory Structure (`backend/`)

```
backend/
├── app/
│   ├── __init__.py           # Flask App Factory & Blueprint registration
│   ├── models/               # SQLAlchemy Data Models
│   │   ├── base.py           # BaseModel & TimestampAuditMixin
│   │   ├── company.py        # Tenant company model
│   │   ├── user.py           # User model
│   │   ├── role.py           # Role model
│   │   ├── department.py     # Department model
│   │   ├── module.py         # Provisioned modules model
│   │   ├── module_action.py  # Module actions model
│   │   ├── user_role.py      # User role mapping model
│   │   ├── role_permission.py# Role permission mapping model
│   │   ├── user_permission.py# User permission override model
│   │   ├── election.py      # Election model
│   │   ├── ballot.py        # Ballot model
│   │   ├── candidate.py     # Candidate model
│   │   ├── voter.py         # Voter model
│   │   ├── voter_registration.py # Voter registration model
│   │   ├── vote.py          # Sealed vote model
│   │   └── audit_log.py     # Audit log model
│   ├── routes/               # Modular REST API Blueprints
│   │   ├── auth.py           # Unified login & password reset
│   │   ├── companies.py      # Platform admin company CRUD
│   │   ├── users.py          # User management
│   │   ├── roles.py          # Role management
│   │   ├── departments.py    # Department management
│   │   ├── modules.py        # Module provisioning
│   │   ├── module_actions.py # Action provisioning
│   │   ├── permissions.py    # Permission mappings
│   │   ├── user_roles.py     # User-role assignments
│   │   ├── elections.py      # Election lifecycle & tallying
│   │   ├── ballots.py        # Ballot management
│   │   ├── candidates.py     # Candidate management
│   │   ├── voters.py         # Voter management
│   │   ├── voter_registrations.py # Registration workflows
│   │   ├── votes.py          # Vote casting & tallying API
│   │   └── audit.py          # Audit trail logging API
│   └── utils/                # Reusable Security & Helper Modules
│       ├── __init__.py       # Authz permission checking logic
│       ├── validators.py     # Centralized input validation
│       ├── db_utils.py       # safe_commit database wrapper
│       ├── constants.py      # System constants & HTTP codes
│       └── audit.py          # @audit_action decorator
├── migrations/               # Alembic database migration scripts
├── tests/                    # Backend Automated Diagnostic Test Suite
│   └── test_authz_refactor.py# Comprehensive 70+ test authorization suite
├── run.py                    # Flask development server runner
├── seed_data.py              # Platform Administrator seed script
├── requirements.txt          # Python dependency requirements
└── .env                      # Environment configuration variables
```

---

## Frontend Directory Structure (`frontend/`)

```
frontend/
├── public/                   # Static HTML assets & icons
├── src/
│   ├── components/           # Reusable UI & Context Components
│   │   ├── AuthContext.js    # Global JWT & authentication state
│   │   ├── PermissionContext.js # Granted module permissions & dynamic menu
│   │   ├── PermissionGuard.js # Route permission protection wrapper
│   │   └── Layout.js         # Navigation header & dynamic sidebar layout
│   ├── pages/                # Page Views & DataGrid Dashboards
│   │   ├── Login.js          # Unified login view
│   │   ├── Companies.js      # Platform Admin company management
│   │   ├── Users.js          # User management dashboard
│   │   ├── Roles.js          # Role & permission editor
│   │   ├── Departments.js    # Department management
│   │   ├── Elections.js      # Election dashboard & workflow stepper
│   │   ├── ElectionWorkflow.js # Election state management view
│   │   ├── ElectionResults.js# Turnout & candidate vote charts
│   │   ├── Ballots.js        # Ballot creation & publishing
│   │   ├── Candidates.js     # Candidate management
│   │   ├── Voters.js         # Voter directory dashboard
│   │   ├── VoterRegistrations.js # Voter approval workflow toolbar
│   │   ├── Votes.js          # Vote monitoring & tallying view
│   │   └── AuditLogs.js      # Audit log viewer
│   ├── App.js                # React Router navigation map
│   └── index.js              # React application entry point
└── package.json              # React dependencies & scripts
```

---

## Documentation Directory Structure (`docs/`)

```
docs/
├── 01_SYSTEM_WORKFLOW_AND_ARCHITECTURE.md    # Multi-tenant domain model & IST timezone
├── 02_CODING_AND_SECURITY_STANDARDS.md       # OOP standards & centralized validators.py
├── 03_DATABASE_SCHEMA_AND_MODELS.md          # Complete ER diagram & table specifications
├── 04_API_REFERENCE_AND_ENDPOINTS.md         # Full REST API endpoint reference
├── 05_BACKEND_AND_AUTOMATED_TESTING_PLAYBOOK.md # Backend diagnostic testing playbook
├── 06_FRONTEND_AND_UI_TESTING_PLAYBOOK.md    # React UI testing & persona QA scenarios
├── 07_ENHANCEMENTS_AND_FUTURE_ROADMAP.md     # Consolidates all legacy specs & roadmap
├── 08_PROJECT_FOLDER_STRUCTURE.md            # Directory map & codebase organization
├── PROJECT_INSTRUCTIONS.md                   # Developer & AI assistant directives
└── archive/                                  # Archived legacy README specifications
```
