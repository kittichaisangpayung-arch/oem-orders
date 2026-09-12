# OEM Orders - Deployment Guide

## PythonAnywhere Deployment

### Prerequisites
- PythonAnywhere free account: https://www.pythonanywhere.com/registration/register/beginner/

### Step-by-Step Deployment

#### 1. Create PythonAnywhere Account
- Sign up at https://www.pythonanywhere.com
- Go to "Web" tab → "Add a new web app"
- Choose "Manual configuration" → Python 3.9

#### 2. Clone Repository
Open a Bash console and run:
```bash
git clone https://github.com/kittichaisangpayung-arch/oem-orders.git
cd oem-orders
```

#### 3. Create Virtual Environment
```bash
mkvirtualenv --python=/usr/bin/python3.9 oem-orders
pip install -r requirements.txt
```

#### 4. Configure Django Settings
```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

#### 5. Configure WSGI File
Go to "Web" tab → Click on WSGI configuration file and replace content with:
```python
import os
import sys

path = '/home/YOUR_USERNAME/oem-orders'
if path not in sys.path:
    sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'oem_orders.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

#### 6. Set Up Static Files
In "Web" tab → Static files section:
- URL: `/static/`
- Directory: `/home/YOUR_USERNAME/oem-orders/staticfiles_build/static`

#### 7. Reload Web App
Click "Reload" button in Web tab

### Access Your App
Your app will be available at: `https://YOUR_USERNAME.pythonanywhere.com`

### Environment Variables (Optional)
For production, add to WSGI file:
```python
os.environ['SECRET_KEY'] = 'your-secret-key-here'
os.environ['DEBUG'] = 'False'
```

## Local Development

### Run locally:
```bash
python manage.py runserver
```

### Run tests:
```bash
pytest
```

## Project Structure
- `apps/` - Django applications
- `oem_orders/` - Main project settings
- `templates/` - HTML templates
- `media/` - User uploaded files
- `staticfiles_build/` - Collected static files

## Features
- PDF parsing and document management
- Purchase order tracking
- Delivery note generation
- Claims management
- Role-based access control
- Production dashboard
