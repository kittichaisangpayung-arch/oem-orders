#!/bin/bash

################################################################################
# PythonAnywhere One-Click Deployment Script
# Run this on PythonAnywhere console to deploy from GitHub
################################################################################

set -e  # Exit on error

echo "================================================================================"
echo "  OEM Orders - PythonAnywhere Deployment"
echo "================================================================================"
echo ""

# Get PythonAnywhere username
if [ -z "$USER" ]; then
    read -p "Enter your PythonAnywhere username: " PA_USERNAME
else
    PA_USERNAME="$USER"
fi

echo "Deploying for user: $PA_USERNAME"
echo ""

# Configuration
REPO_URL="https://github.com/kittichaisangpayung-arch/oem-orders.git"
PROJECT_DIR="$HOME/oem-orders"
VENV_DIR="$PROJECT_DIR/venv"
PYTHON_VERSION="python3.10"

################################################################################
# Step 1: Clone or Update Repository
################################################################################
echo "📦 Step 1: Checking repository..."
if [ -d "$PROJECT_DIR" ]; then
    echo "   Project exists. Pulling latest changes..."
    cd "$PROJECT_DIR"
    git pull origin main
else
    echo "   Cloning repository..."
    cd "$HOME"
    git clone "$REPO_URL"
fi

cd "$PROJECT_DIR"
echo "   ✓ Repository ready"
echo ""

################################################################################
# Step 2: Create Virtual Environment
################################################################################
echo "🐍 Step 2: Setting up Python environment..."
if [ -d "$VENV_DIR" ]; then
    echo "   Virtual environment exists"
else
    echo "   Creating virtual environment..."
    $PYTHON_VERSION -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
echo "   ✓ Virtual environment activated"
echo ""

################################################################################
# Step 3: Install Dependencies
################################################################################
echo "📚 Step 3: Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "   ✓ Dependencies installed"
echo ""

################################################################################
# Step 4: Create .env File
################################################################################
echo "⚙️  Step 4: Creating environment configuration..."
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cat > "$PROJECT_DIR/.env" << EOF
DEBUG=False
ALLOWED_HOSTS=${PA_USERNAME}.pythonanywhere.com,localhost,127.0.0.1
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
DATABASE_URL=sqlite:///db.sqlite3
EOF
    echo "   ✓ .env file created"
else
    echo "   .env file already exists (skipping)"
fi
echo ""

################################################################################
# Step 5: Database Setup
################################################################################
echo "🗄️  Step 5: Setting up database..."
python manage.py migrate --noinput
echo "   ✓ Database migrations completed"
echo ""

################################################################################
# Step 6: Collect Static Files
################################################################################
echo "🎨 Step 6: Collecting static files..."
python manage.py collectstatic --noinput
echo "   ✓ Static files collected"
echo ""

################################################################################
# Step 7: Test Parsers
################################################################################
echo "🧪 Step 7: Testing parsers..."
python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.parsers.registry import _REGISTRY
print('   Registered parsers:', sorted(_REGISTRY.keys()))
" 2>/dev/null || echo "   ⚠ Parser test skipped"
echo ""

################################################################################
# Step 8: Generate WSGI Configuration
################################################################################
echo "📝 Step 8: Generating WSGI configuration..."
WSGI_FILE="$PROJECT_DIR/wsgi_config_${PA_USERNAME}.py"
cat > "$WSGI_FILE" << EOF
# +++++++++++ DJANGO +++++++++++
# WSGI Configuration for OEM Orders
# Copy this to: /var/www/${PA_USERNAME}_pythonanywhere_com_wsgi.py

import os
import sys

# Add project directory to path
project_home = '/home/${PA_USERNAME}/oem-orders'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set Django settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

# Activate virtual environment
venv_path = '/home/${PA_USERNAME}/oem-orders/venv/lib/python3.10/site-packages'
if venv_path not in sys.path:
    sys.path.insert(0, venv_path)

# Import Django WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
EOF

echo "   ✓ WSGI configuration generated: $WSGI_FILE"
echo ""

################################################################################
# Step 9: Create Update Script
################################################################################
echo "🔄 Step 9: Creating update script..."
cat > "$PROJECT_DIR/update.sh" << 'EOF'
#!/bin/bash
set -e
cd ~/oem-orders
source venv/bin/activate
echo "Pulling latest changes..."
git pull origin main
echo "Updating dependencies..."
pip install -r requirements.txt --upgrade -q
echo "Running migrations..."
python manage.py migrate --noinput
echo "Collecting static files..."
python manage.py collectstatic --noinput
echo "✓ Update complete! Remember to reload your web app."
EOF

chmod +x "$PROJECT_DIR/update.sh"
echo "   ✓ Update script created: $PROJECT_DIR/update.sh"
echo ""

################################################################################
# Deployment Summary
################################################################################
echo "================================================================================"
echo "  ✅ DEPLOYMENT COMPLETE!"
echo "================================================================================"
echo ""
echo "📋 Next Steps (Manual Configuration Required):"
echo ""
echo "1️⃣  Configure WSGI File:"
echo "   • Go to PythonAnywhere Web tab"
echo "   • Click on WSGI configuration file"
echo "   • Delete all content and copy from:"
echo "     cat $WSGI_FILE"
echo ""
echo "2️⃣  Configure Static Files (in Web tab):"
echo "   URL: /static/"
echo "   Directory: /home/${PA_USERNAME}/oem-orders/staticfiles/"
echo ""
echo "3️⃣  Configure Media Files (optional, in Web tab):"
echo "   URL: /media/"
echo "   Directory: /home/${PA_USERNAME}/oem-orders/media/"
echo ""
echo "4️⃣  Create Superuser (optional):"
echo "   cd ~/oem-orders"
echo "   source venv/bin/activate"
echo "   python manage.py createsuperuser"
echo ""
echo "5️⃣  Reload Web App:"
echo "   • Go to Web tab"
echo "   • Click the green 'Reload' button"
echo ""
echo "6️⃣  Visit Your Site:"
echo "   https://${PA_USERNAME}.pythonanywhere.com"
echo ""
echo "================================================================================"
echo "📝 Quick Commands:"
echo "================================================================================"
echo ""
echo "# Update deployment:"
echo "~/oem-orders/update.sh"
echo ""
echo "# View WSGI config:"
echo "cat $WSGI_FILE"
echo ""
echo "# Django shell:"
echo "cd ~/oem-orders && source venv/bin/activate && python manage.py shell"
echo ""
echo "# View logs:"
echo "tail -f /var/log/${PA_USERNAME}.pythonanywhere.com.error.log"
echo ""
echo "================================================================================"
