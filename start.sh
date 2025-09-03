#!/bin/sh

echo "Inside start.sh"
echo "PORT value: $PORT"

PORT=${PORT:-8000}
echo "Starting server on port $PORT"

exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"