#!/bin/bash
set -e

# Wait for database
echo "Waiting for database..."
while ! python -c "
import os
import psycopg
conn = psycopg.connect(
    host=os.environ.get('POSTGRES_HOST', 'localhost'),
    port=os.environ.get('POSTGRES_PORT', '5432'),
    dbname=os.environ.get('POSTGRES_DB', 'diveops'),
    user=os.environ.get('POSTGRES_USER', 'postgres'),
    password=os.environ.get('POSTGRES_PASSWORD', 'postgres')
)
conn.close()
" 2>/dev/null; do
    echo "Database not ready, waiting..."
    sleep 2
done
echo "Database is ready!"

# Run migrations if MIGRATE=true
if [ "${MIGRATE:-false}" = "true" ]; then
    echo "Running migrations..."
    # Don't fail if migrations have issues - log and continue
    if ! python manage.py migrate --noinput; then
        echo "WARNING: Migrations failed! The app will start but may have issues."
        echo "Check migration state and fix manually if needed."
    fi
fi

# Create superuser if SUPERUSER_EMAIL is set
if [ -n "$SUPERUSER_EMAIL" ] && [ -n "$SUPERUSER_PASSWORD" ]; then
    echo "Creating superuser if not exists..."
    python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='$SUPERUSER_EMAIL').exists():
    User.objects.create_superuser(email='$SUPERUSER_EMAIL', password='$SUPERUSER_PASSWORD')
    print('Superuser created')
else:
    print('Superuser already exists')
"
fi

exec "$@"
