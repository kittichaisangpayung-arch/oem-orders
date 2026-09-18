#!/bin/bash

# สคริปต์สำหรับรันบน PythonAnywhere

# 1. Activate virtualenv (adjust path as needed)
# source /home/terzanalak/.virtualenvs/oem-orders/bin/activate

# 2. Navigate to project
cd ~/oem-orders

# 3. Pull latest code
git pull origin main

# 4. Install/update dependencies
pip install -r requirements.txt

# 5. Run migrations
python manage.py makemigrations
python manage.py migrate

# 6. Collect static files
python manage.py collectstatic --noinput

# 7. Reload web app (adjust URL as needed)
# touch /var/www/terzanalak_pythonanywhere_com_wsgi.py

echo "Deployment complete!"
echo "Next steps:"
echo "1. Go to Web tab"
echo "2. Click 'Reload terzanalak.pythonanywhere.com'"
