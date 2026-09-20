# Deploy to PythonAnywhere Guide

## Prerequisites
- PythonAnywhere account
- GitHub repository: https://github.com/kittichaisangpayung-arch/oem-orders

## Deployment Steps

### 1. Clone Repository on PythonAnywhere

```bash
# SSH into PythonAnywhere console
cd ~
git clone https://github.com/kittichaisangpayung-arch/oem-orders.git
cd oem-orders
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3.10 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### 3. Install Dependencies

```bash
# Install requirements
pip install -r requirements.txt

# If pdfplumber needs additional system packages:
# Contact PythonAnywhere support for poppler-utils installation
```

### 4. Configure Environment Variables

```bash
# Create .env file (or set in PythonAnywhere dashboard)
nano .env
```

Add necessary environment variables:
```
DEBUG=False
ALLOWED_HOSTS=your-username.pythonanywhere.com
SECRET_KEY=your-secret-key-here
DATABASE_URL=your-database-url
```

### 5. Database Setup

```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput
```

### 6. Configure WSGI

Edit `/var/www/your-username_pythonanywhere_com_wsgi.py`:

```python
import os
import sys

# Add your project directory to the sys.path
path = '/home/your-username/oem-orders'
if path not in sys.path:
    sys.path.insert(0, path)

# Set environment variable to point to settings
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

# Activate virtual environment
activate_this = '/home/your-username/oem-orders/venv/bin/activate_this.py'
with open(activate_this) as f:
    exec(f.read(), {'__file__': activate_this})

# Import Django application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### 7. Configure Static Files

In PythonAnywhere Web tab:
- **Static files URL**: `/static/`
- **Static files directory**: `/home/your-username/oem-orders/staticfiles/`

### 8. Configure Media Files (if needed)

- **Media files URL**: `/media/`
- **Media files directory**: `/home/your-username/oem-orders/media/`

### 9. Reload Web App

Click "Reload" button in PythonAnywhere Web tab.

## Update Deployment (Future Updates)

```bash
# SSH into PythonAnywhere
cd ~/oem-orders

# Pull latest changes
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Reload web app from dashboard
```

## Testing Lopia Parser

After deployment, test the parser:

```bash
cd ~/oem-orders
source venv/bin/activate

# Test parser
python manage.py shell
```

In Django shell:
```python
from apps.parsers.registry import get_parser

parser = get_parser("lopia_v1")
# Test with uploaded PDF file
result = parser.parse("/path/to/PO_Lopia.pdf")
print(f"Parsed {len(result.line_items)} items")
```

## Common Issues & Solutions

### Issue: pdfplumber not working
**Solution**: Contact PythonAnywhere support to install `poppler-utils`

### Issue: Static files not loading
**Solution**: 
```bash
python manage.py collectstatic --noinput
# Check static files path in Web tab
```

### Issue: Database connection error
**Solution**: Verify DATABASE_URL in environment variables

### Issue: Import errors
**Solution**: Check PYTHONPATH in WSGI configuration

## Security Checklist

- [ ] Set `DEBUG=False` in production
- [ ] Configure proper `ALLOWED_HOSTS`
- [ ] Use strong `SECRET_KEY`
- [ ] Set up database backups
- [ ] Configure HTTPS (free with Let's Encrypt on PythonAnywhere)
- [ ] Protect sensitive files (.env, credentials.json)
- [ ] Set proper file permissions

## Performance Tips

1. **Enable gzip compression** in settings
2. **Use CDN** for static files (optional)
3. **Configure database connection pooling**
4. **Set up caching** (Redis/Memcached if available)
5. **Monitor error logs** regularly

## Monitoring

Check logs in PythonAnywhere:
- **Error log**: `/var/log/your-username.pythonanywhere.com.error.log`
- **Server log**: `/var/log/your-username.pythonanywhere.com.server.log`

## Support

- PythonAnywhere Forums: https://www.pythonanywhere.com/forums/
- GitHub Issues: https://github.com/kittichaisangpayung-arch/oem-orders/issues
