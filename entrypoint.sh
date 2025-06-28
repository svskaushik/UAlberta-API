#!/bin/sh

echo "Waiting for database to be ready..."
# Wait for database to be available
until python -c "
import psycopg2
import os
import sys
try:
    # Convert the DATABASE_URL from sqlalchemy format to psycopg2 format
    db_url = os.getenv('DATABASE_URL')
    if db_url and 'postgresql+psycopg2://' in db_url:
        db_url = db_url.replace('postgresql+psycopg2://', 'postgresql://')
    elif db_url and 'postgresql://' not in db_url:
        db_url = 'postgresql://postgres:postgres@postgres:5432/university_data'
    
    conn = psycopg2.connect(db_url)
    conn.close()
    print('Database is ready!')
except Exception as e:
    print(f'Database not ready yet... Error: {e}')
    sys.exit(1)
"; do
  echo "Waiting for database..."
  sleep 2
done

echo "Initializing database schema..."
python init_database.py

echo "Starting API server..."
exec python -m uvicorn main:app --host "${API_HOST:-0.0.0.0}" --port "${API_PORT:-8100}"
