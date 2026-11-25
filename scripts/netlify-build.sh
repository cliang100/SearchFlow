#!/bin/sh
# Builds the static UI for Netlify and proxies API calls to the Python server.
set -eu

case "${BACKEND_URL:-}" in
  https://*) ;;
  *) echo "Set BACKEND_URL to the https URL of the API server" >&2; exit 1 ;;
esac
backend="${BACKEND_URL%/}"

rm -rf dist
mkdir dist
cp -r static dist/static
cp static/index.html dist/index.html

# Proxying keeps the API on the same origin, so no CORS setup is needed.
cat > dist/_redirects <<EOF
/search/* $backend/search/:splat 200
/crawler/* $backend/crawler/:splat 200
/documents/* $backend/documents/:splat 200
/ui / 301
EOF

cat > dist/_headers <<EOF
/*
  Content-Security-Policy: default-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
EOF
