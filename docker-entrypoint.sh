#!/bin/bash
set -e

echo "=== Starting TVPL Crawler API ==="

# Setup database if needed
if [ -f "setup_database.py" ]; then
    echo "Running database setup..."
    python setup_database.py || echo "Database setup skipped or failed"
fi

# Start Xvfb in background
echo "Starting Xvfb..."
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99

# Wait for Xvfb to start
sleep 2

# Start API
echo "Starting FastAPI server..."
exec uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
