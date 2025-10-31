#!/bin/bash
set -e

echo "🚀 Starting TVPL Crawler API..."

# Wait for PostgreSQL
echo "⏳ Waiting for PostgreSQL..."
while ! python -c "import psycopg2; psycopg2.connect(host='$DB_HOST', port='$DB_PORT', user='$DB_USER', password='$DB_PASSWORD', dbname='$DB_NAME')" 2>/dev/null; do
  sleep 2
done
echo "✅ PostgreSQL is ready!"

# Auto setup database
echo "🔧 Setting up database..."
python setup_database.py || echo "⚠️ Database setup failed, continuing..."

# Start FastAPI
echo "🌐 Starting FastAPI server..."
exec uvicorn api.main:app --host 0.0.0.0 --port 8000 --no-access-log