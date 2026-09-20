#!/bin/bash

# PythonAnywhere Update Script
# Run this when you want to pull latest changes and update deployment

set -e  # Exit on error

echo "========================================="
echo "PythonAnywhere Update Script"
echo "========================================="
echo ""

# Configuration
PROJECT_DIR="$HOME/oem-orders"
VENV_DIR="$PROJECT_DIR/venv"

# Check if project exists
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ Error: Project directory not found at $PROJECT_DIR"
    echo "Run deploy_to_pythonanywhere.sh first!"
    exit 1
fi

cd "$PROJECT_DIR"

# Step 1: Pull latest changes
echo "✓ Pulling latest changes from GitHub..."
git pull origin main

# Step 2: Activate virtual environment
echo "✓ Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Step 3: Update dependencies
echo "✓ Updating dependencies..."
pip install -r requirements.txt --upgrade

# Step 4: Run migrations
echo "✓ Running migrations..."
python manage.py migrate

# Step 5: Collect static files
echo "✓ Collecting static files..."
python manage.py collectstatic --noinput

# Step 6: Run tests (optional)
echo "✓ Running tests..."
python manage.py test apps.parsers.tests.test_lopia_parser -v 2 || echo "⚠ Some tests failed"

echo ""
echo "========================================="
echo "✅ Update Complete!"
echo "========================================="
echo ""
echo "⚠ Don't forget to reload your web app in PythonAnywhere dashboard!"
echo ""
