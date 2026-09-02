#!/bin/bash

# setup.sh — Automated setup for AcademicGuard

# 1. Create .env if not exists
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    
    # Generate random JWT secret
    JWT_SECRET=$(openssl rand -hex 32)
    sed -i "s/CHANGE_ME_TO_64_CHAR_RANDOM_STRING/$JWT_SECRET/g" .env
    sed -i "s/CHANGE_ME_STRONG_PASSWORD/$(openssl rand -hex 12)/g" .env
    
    echo ".env created with random secrets."
else
    echo ".env already exists. Skipping."
fi

# 2. Setup Nginx certs for the optional production-style compose stack
CERT_DIR="./nginx/certs"
if [ ! -d "$CERT_DIR" ]; then
    echo "Creating $CERT_DIR and generating self-signed certificates for the production-style stack..."
    mkdir -p "$CERT_DIR"
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$CERT_DIR/privkey.pem" \
        -out "$CERT_DIR/fullchain.pem" \
        -subj "/C=US/ST=State/L=City/O=AcademicGuard/CN=localhost"
    echo "Certificates generated."
else
    echo "$CERT_DIR already exists. Skipping certificate generation."
fi

# 3. Inform user about next steps
echo "------------------------------------------------------------"
echo "Setup complete! You can now start the application with:"
echo "  docker compose up -d --build"
echo ""
echo "Default local app URL: http://localhost:8080"
echo "Default API docs URL: http://localhost:8000/api/docs"
echo ""
echo "For the production-style nginx/TLS stack, run:"
echo "  docker compose -f docker-compose.prod.yml up -d --build"
echo "and add '127.0.0.1 academicguard.example.com' to your /etc/hosts if testing locally."
echo "------------------------------------------------------------"
