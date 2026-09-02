#!/bin/bash
set -e

# Automatically detect PostgreSQL version and binary path
PG_VERSION=$(ls /usr/lib/postgresql/ | head -n 1)
PG_BIN="/usr/lib/postgresql/$PG_VERSION/bin"
PG_DATA="/var/lib/postgresql/data/pg_data"

# Create a symlink so "postgres" command works everywhere
ln -sf "$PG_BIN/postgres" /usr/bin/postgres
ln -sf "$PG_BIN/pg_ctl" /usr/bin/pg_ctl
ln -sf "$PG_BIN/psql" /usr/bin/psql
ln -sf "$PG_BIN/initdb" /usr/bin/initdb
ln -sf "$PG_BIN/pg_isready" /usr/bin/pg_isready

# Fix socket and log directories
mkdir -p /var/run/postgresql && chown -R postgres:postgres /var/run/postgresql
mkdir -p /var/log/postgresql && chown -R postgres:postgres /var/log/postgresql

# 1. Initialize PostgreSQL if not already initialized
if [ ! -d "$PG_DATA" ]; then
    echo "Initializing PostgreSQL $PG_VERSION data directory..."
    mkdir -p "$PG_DATA"
    chown -R postgres:postgres /var/lib/postgresql/data
    sudo -u postgres "$PG_BIN/initdb" -D "$PG_DATA"

    # Enable TCP/IP connections (needed for the API to connect via 127.0.0.1)
    echo "listen_addresses = '127.0.0.1'" >> "$PG_DATA/postgresql.conf"
    echo "host all all 127.0.0.1/32 md5" >> "$PG_DATA/pg_hba.conf"
fi

# Cleanup any stale lock files from previous runs
rm -f "$PG_DATA/postmaster.pid"

# 2. Start PostgreSQL temporarily to create user and database
echo "Starting PostgreSQL..."
sudo -u postgres "$PG_BIN/pg_ctl" -D "$PG_DATA" -l /var/log/postgresql/postgresql.log start

# Wait for Postgres to be ready
until sudo -u postgres "$PG_BIN/pg_isready"; do
  echo "Waiting for PostgreSQL..."
  sleep 2
done

# Create user and database
DB_USER=${POSTGRES_USER:-academicguard}
DB_NAME=${POSTGRES_DB:-academicguard}
DB_PASS=${POSTGRES_PASSWORD:-b53fcee4e923d5b51109fc46}

echo "Setting up database '$DB_NAME' for user '$DB_USER'..."
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" 2>/dev/null || true
sudo -u postgres psql -c "ALTER USER $DB_USER WITH SUPERUSER;" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || true

# 3. Initialize tables and seed admin user via Python
echo "Initializing database tables and seeding admin user..."
cd /app/backend
PYTHONPATH=. python -c "
from app.core.security import hash_password
import psycopg2

conn = psycopg2.connect(
    host='/var/run/postgresql',
    dbname='$DB_NAME',
    user='$DB_USER',
    password='$DB_PASS'
)
cur = conn.cursor()

# Create users table if it doesn't exist
cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        hashed_password VARCHAR(255) NOT NULL,
        full_name VARCHAR(255),
        role VARCHAR(50) DEFAULT ''admin'',
        is_active BOOLEAN DEFAULT true,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
    )
''')

# Seed admin user
pw = hash_password('Password123!')
cur.execute('''
    INSERT INTO users (email, hashed_password, full_name, role, is_active)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (email) DO NOTHING
''', ('admin@academicguard.ai', pw, 'System Administrator', 'admin', True))

conn.commit()
cur.close()
conn.close()
print('Database tables initialized and admin user seeded.')
" || echo "Warning: seed script had issues, API will create tables on startup."

cd /

# 4. Stop PostgreSQL so Supervisor can take over
sudo -u postgres "$PG_BIN/pg_ctl" -D "$PG_DATA" stop

# 5. Start Supervisor (manages Nginx, Postgres, Redis, and FastAPI)
echo "Starting All-in-One Services via Supervisor..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
