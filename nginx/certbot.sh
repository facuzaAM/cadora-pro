#!/bin/sh
set -e

DOMAIN="${DOMAIN:-cadora.pro}"
EMAIL="${CERTBOT_EMAIL:-hello@cadora.pro}"
MARKER="/etc/letsencrypt/.issued"
RENEWAL_CONF="/etc/letsencrypt/renewal/$DOMAIN.conf"

# A broken/empty renewal config would break every future renewal, so force a
# fresh issuance (which also rewrites the renewal metadata) when it is missing.
if [ ! -s "$RENEWAL_CONF" ]; then
    rm -f "$MARKER"
fi

# Only force a reissue while no real certificate exists yet.
# nginx generates a self-signed placeholder in the same directory so it can
# boot before DNS/ACME are ready; forcing a reissue replaces it with the
# real Let's Encrypt certificate exactly once.
if [ ! -f "$MARKER" ]; then
    if ! certbot certonly --webroot -w /var/www/certbot \
        --email "$EMAIL" --agree-tos --no-eff-email \
        -d "$DOMAIN" -d "www.$DOMAIN" -d "api.$DOMAIN" \
        --force-renewal; then
        echo "certbot issuance failed, retrying in 60s..."
        sleep 60
        exit 1
    fi
    touch "$MARKER"
fi

trap 'exit 0' TERM
while :; do
    certbot renew --webroot -w /var/www/certbot --quiet
    sleep 12h &
    wait $!
done
