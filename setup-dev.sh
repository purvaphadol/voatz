#!/bin/bash

# Flask Access Control System - Development Setup Script

set -e

echo "🚀 Setting up Flask Access Control System for Development"
echo "========================================================"

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Backend Setup
echo "📦 Setting up Backend..."
cd backend

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit backend/.env with your database credentials!"
fi

cd ..

# Frontend Setup
echo "📦 Setting up Frontend..."
cd frontend

# Install Node.js dependencies
if [ ! -d "node_modules" ]; then
    echo "Installing Node.js dependencies..."
    npm install
fi

cd ..

echo "✅ Setup completed!"
echo ""
echo "🔧 Next Steps:"
echo "1. Edit backend/.env with your database credentials"
echo "2. Start PostgreSQL database"
echo "3. Run database migrations: cd backend && flask db upgrade"
echo "4. Seed initial data: cd backend && python seed_data.py"
echo "5. Start backend: cd backend && python app.py"
echo "6. Start frontend: cd frontend && npm start"
echo ""
echo "🐳 Or use Docker:"
echo "docker-compose up --build"
echo ""
echo "🌐 Access the application:"
echo "- Frontend: http://localhost:3000"
echo "- Backend: http://localhost:5000"
echo "- Default login: rushiraj@datagrid.co.in / admin123"
