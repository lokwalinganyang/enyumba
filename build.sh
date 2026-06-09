#!/bin/bash

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Running migrations..."
python manage.py migrate --noinput

echo "Creating superuser (if not exists)..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model;
User = get_user_model();
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@enyumba.com', 'admin123')
    print("Superuser 'admin' created.")
else:
    print("Superuser already exists.")
EOF

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Build completed!"