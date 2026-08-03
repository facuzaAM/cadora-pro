#!/bin/sh
set -e

DOMAIN="${DOMAIN:-cadora.pro}"
CERT_DIR="/etc/letsencrypt/live/$DOMAIN"

if [ ! -f "$CERT_DIR/fullchain.pem" ]; then
    echo "Generando certificado autofirmado temporal para $DOMAIN..."
    mkdir -p "$CERT_DIR"
    openssl req -x509 -nodes -newkey rsa:2048 \
        -keyout "$CERT_DIR/privkey.pem" \
        -out "$CERT_DIR/fullchain.pem" \
        -days 1 \
        -subj "/CN=$DOMAIN"
fi

# Reload periodically so nginx picks up renewed certificates from certbot
(while :; do
    sleep 12h
    nginx -s reload 2>/dev/null || true
done) &

exec nginx -g "daemon off;"
