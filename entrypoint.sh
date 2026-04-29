#!/bin/sh

set -e  # Exit on error

# Ensure logs and db_data directories exist (may be empty if volumes are freshly mounted)
mkdir -p /app/logs /app/db_data

# Generate a secret key if not provided via environment
if [ -z "$DJANGO_SECRET_KEY" ]; then
    export DJANGO_SECRET_KEY=$(python -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits + '!@#$%^&*(-_=+)') for _ in range(64)))")
    echo "WARNING: DJANGO_SECRET_KEY not set — generated a temporary key. Set it explicitly for persistence."
fi

# Warn if CSRF trusted origins not set
if [ -z "$DJANGO_CSRF_TRUSTED_ORIGINS" ]; then
    echo "WARNING: DJANGO_CSRF_TRUSTED_ORIGINS not set. POST requests may fail if accessed by hostname/IP."
    echo "  Set it to e.g.: http://192.168.1.100,http://localhost"
fi

echo "Running migrations..."
python manage.py migrate --noinput

echo "Loading initial data if needed..."
python manage.py load_initial_if_empty

# Start Nginx in the background
nginx -g 'daemon on;'

# Start Uvicorn in the foreground
# Adjust host and port as needed; no Unix socket by default
exec uvicorn BBulkSmash_project.asgi:application \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 1 \
    --proxy-headers \
    --forwarded-allow-ips=127.0.0.1

