#!/bin/bash

# PythonAnywhere Deployment Script
# Run this script on PythonAnywhere console

set -e  # Exit on error

echo "========================================="
echo "PythonAnywhere Deployment Script"
echo "========================================="
echo ""

# Configuration - EDIT THESE VALUES
PYTHONANYWHERE_USERNAME="your-username"  # Change to your PythonAnywhere username
PROJECT_DIR="$HOME/oem-orders"
VENV_DIR="$PROJECT_DIR/venv"
REPO_URL="https://github.com/kittichaisangpayung-arch/oem-orders.git"

echo "Configuration:"
echo "  Username: $PYTHONANYWHERE_USERNAME"
echo "  Project Dir: $PROJECT_DIR"
echo "  Repository: $REPO_URL"
echo ""

# Step 1: Clone or Update Repository
if [ -d "$PROJECT_DIR" ]; then
    echo "✓ Project directory exists, pulling latest changes..."
    cd "$PROJECT_DIR"
    git pull origin main
else
    echo "✓ Cloning repository..."
    cd "$HOME"
    git clone "$REPO_URL"
    cd "$PROJECT_DIR"
fi

# Step 2: Create Virtual Environment
if [ -d "$VENV_DIR" ]; then
    echo "✓ Virtual environment exists"
else
    echo "✓ Creating virtual environment..."
    python3.10 -m venv "$VENV_DIR"
fi

# Step 3: Activate Virtual Environment
echo "✓ Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Step 4: Upgrade pip
echo "✓ Upgrading pip..."
pip install --upgrade pip

# Step 5: Install Dependencies
echo "✓ Installing dependencies..."
pip install -r requirements.txt

# Step 6: Create .env file if not exists
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "⚠ Creating .env file (you need to edit this manually)..."
    cat > "$PROJECT_DIR/.env" << 'EOF'
DEBUG=False
ALLOWED_HOSTS=your-username.pythonanywhere.com
SECRET_KEY=change-this-to-a-random-secret-key
DATABASE_URL=sqlite:///db.sqlite3
EOF
    echo "⚠ Please edit .env file with your actual settings!"
fi

# Step 7: Run Migrations
echo "✓ Running migrations..."
python manage.py migrate

# Step 8: Collect Static Files
echo "✓ Collecting static files..."
python manage.py collectstatic --noinput

# Step 9: Test Lopia Parser
echo "✓ Testing Lopia parser..."
python -c "
import sys
sys.path.insert(0, '$PROJECT_DIR')
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.parsers.registry import _REGISTRY
print('Registered parsers:', sorted(_REGISTRY.keys()))
" || echo "⚠ Parser test skipped (Django may not be configured yet)"

echo ""
echo "========================================="
echo "✅ Deployment Complete!"
echo "========================================="
echo ""
echo "Next Steps:"
echo "1. Edit .env file: nano $PROJECT_DIR/.env"
echo "2. Create superuser: python manage.py createsuperuser"
echo "3. Configure WSGI file (see instructions below)"
echo "4. Reload web app from PythonAnywhere dashboard"
echo ""
echo "WSGI Configuration:"
echo "  Edit: /var/www/${PYTHONANYWHERE_USERNAME}_pythonanywhere_com_wsgi.py"
echo "  Use the template in PYTHONANYWHERE_DEPLOYMENT.md"
echo ""
echo "Static Files Configuration (in Web tab):"
echo "  URL: /static/"
echo "  Directory: $PROJECT_DIR/staticfiles/"
echo ""
