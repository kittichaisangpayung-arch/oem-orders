# PythonAnywhere Deployment - Bash Commands

## Quick Start Guide

### 1. Initial Deployment (ครั้งแรก)

```bash
# SSH into PythonAnywhere console
ssh your-username@ssh.pythonanywhere.com

# Run deployment script
cd ~
git clone https://github.com/kittichaisangpayung-arch/oem-orders.git
cd oem-orders

# Edit username in script first
nano deploy_to_pythonanywhere.sh
# Change: PYTHONANYWHERE_USERNAME="your-username"

# Make script executable
chmod +x deploy_to_pythonanywhere.sh

# Run deployment
./deploy_to_pythonanywhere.sh
```

### 2. Configure WSGI

```bash
# Generate WSGI configuration
cd ~/oem-orders
chmod +x create_wsgi_config.sh
./create_wsgi_config.sh

# The script will create a WSGI file and show you the content
# Copy the content and paste it to PythonAnywhere Web tab > WSGI config file
```

### 3. Update Deployment (ครั้งต่อไป)

```bash
# SSH into PythonAnywhere
cd ~/oem-orders

# Make script executable (first time only)
chmod +x update_pythonanywhere.sh

# Run update
./update_pythonanywhere.sh

# Then reload web app from PythonAnywhere dashboard
```

---

## Manual Step-by-Step Commands

### Initial Setup

```bash
# 1. Clone repository
cd ~
git clone https://github.com/kittichaisangpayung-arch/oem-orders.git
cd oem-orders

# 2. Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# 3. Upgrade pip
pip install --upgrade pip

# 4. Install dependencies
pip install -r requirements.txt

# 5. Create .env file
nano .env
```

Add to `.env`:
```env
DEBUG=False
ALLOWED_HOSTS=your-username.pythonanywhere.com
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///db.sqlite3
```

```bash
# 6. Run migrations
python manage.py migrate

# 7. Create superuser
python manage.py createsuperuser

# 8. Collect static files
python manage.py collectstatic --noinput

# 9. Test parsers
python manage.py shell
```

In Django shell:
```python
from apps.parsers.registry import _REGISTRY
print("Registered parsers:", sorted(_REGISTRY.keys()))

from apps.parsers.registry import get_parser
parser = get_parser("lopia_v1")
print("Lopia parser loaded successfully!")
exit()
```

### Update Existing Deployment

```bash
# 1. Go to project directory
cd ~/oem-orders

# 2. Activate virtual environment
source venv/bin/activate

# 3. Pull latest changes
git pull origin main

# 4. Update dependencies
pip install -r requirements.txt --upgrade

# 5. Run migrations
python manage.py migrate

# 6. Collect static files
python manage.py collectstatic --noinput

# 7. Test (optional)
python manage.py test apps.parsers.tests.test_lopia_parser

# 8. Reload web app from dashboard
```

---

## PythonAnywhere Web Configuration

### Static Files (in Web tab)
```
URL: /static/
Directory: /home/your-username/oem-orders/staticfiles/
```

### Media Files (in Web tab)
```
URL: /media/
Directory: /home/your-username/oem-orders/media/
```

### WSGI Configuration
Edit: `/var/www/your-username_pythonanywhere_com_wsgi.py`

```python
import os
import sys

# Add project to path
project_home = '/home/your-username/oem-orders'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Django settings
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

# Activate venv
venv_path = '/home/your-username/oem-orders/venv/lib/python3.10/site-packages'
if venv_path not in sys.path:
    sys.path.insert(0, venv_path)

# Django WSGI
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

---

## Testing Commands

```bash
# Test Lopia parser
cd ~/oem-orders
source venv/bin/activate

python manage.py test apps.parsers.tests.test_lopia_parser -v 2

# Test all parsers
python manage.py test apps.parsers.tests -v 2

# Check parser registry
python -c "
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.parsers.registry import _REGISTRY
print('Available parsers:', sorted(_REGISTRY.keys()))
"
```

---

## Troubleshooting Commands

```bash
# Check Python version
python --version

# Check pip packages
pip list

# Check Django settings
python manage.py check

# Run Django shell
python manage.py shell

# View logs
tail -f /var/log/your-username.pythonanywhere.com.error.log

# Check database
python manage.py dbshell

# Create migrations (if needed)
python manage.py makemigrations

# Show migrations
python manage.py showmigrations
```

---

## Useful Aliases (Optional)

Add to `~/.bashrc`:

```bash
# PythonAnywhere shortcuts
alias pa-activate='cd ~/oem-orders && source venv/bin/activate'
alias pa-update='cd ~/oem-orders && ./update_pythonanywhere.sh'
alias pa-logs='tail -f /var/log/*.error.log'
alias pa-shell='cd ~/oem-orders && source venv/bin/activate && python manage.py shell'
```

Apply changes:
```bash
source ~/.bashrc
```

---

## Complete Deployment Checklist

- [ ] Clone repository: `git clone https://github.com/kittichaisangpayung-arch/oem-orders.git`
- [ ] Create venv: `python3.10 -m venv venv`
- [ ] Activate venv: `source venv/bin/activate`
- [ ] Install packages: `pip install -r requirements.txt`
- [ ] Create .env file with proper settings
- [ ] Run migrations: `python manage.py migrate`
- [ ] Create superuser: `python manage.py createsuperuser`
- [ ] Collect static: `python manage.py collectstatic --noinput`
- [ ] Configure WSGI file in Web tab
- [ ] Set static files path in Web tab: `/static/` → `staticfiles/`
- [ ] Set media files path in Web tab: `/media/` → `media/`
- [ ] Reload web app
- [ ] Test site: visit `https://your-username.pythonanywhere.com`
- [ ] Test admin: visit `https://your-username.pythonanywhere.com/admin`
- [ ] Test Lopia parser in Django shell

---

## Quick Reference

```bash
# One-liner deployment (after initial setup)
cd ~/oem-orders && source venv/bin/activate && git pull && pip install -r requirements.txt --upgrade && python manage.py migrate && python manage.py collectstatic --noinput

# One-liner test
cd ~/oem-orders && source venv/bin/activate && python manage.py test apps.parsers.tests.test_lopia_parser
```
