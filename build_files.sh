#!/bin/bash

echo "Installing dependencies..."
# Add the '--break-system-packages' flag to fix the external environment error
python3 -m pip install --break-system-packages -r requirements.txt

echo "Running migrations..."
python3 manage.py migrate --noinput

echo "Collecting static files..."
python3 manage.py collectstatic --noinput --clear

echo "Build completed."