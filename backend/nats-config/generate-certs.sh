#!/bin/bash
# NATS TLS Certificate Generator for PMOVES-DoX
# Generates self-signed certificates for secure NATS connections
#
# Usage: ./generate-certs.sh [output-dir]
# Default output: ./certs/

set -e

CERT_DIR="${1:-certs}"
DAYS_VALID=365
KEY_SIZE=4096

# Certificate subject fields
COUNTRY="US"
STATE="California"
LOCALITY="San Francisco"
ORG="PMOVES"
OU="DoX"
CN="nats.pmoves.local"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check for OpenSSL
if ! command -v openssl &> /dev/null; then
    log_error "OpenSSL is required but not installed."
    exit 1
fi

# Create certificate directory
mkdir -p "$CERT_DIR"
cd "$CERT_DIR"

log_info "Generating certificates in: $(pwd)"

# 1. Generate CA private key and certificate
log_info "Generating Certificate Authority (CA)..."
openssl genrsa -out ca.key $KEY_SIZE 2>/dev/null

openssl req -new -x509 -days $DAYS_VALID -key ca.key -out ca.crt \
    -subj "/C=$COUNTRY/ST=$STATE/L=$LOCALITY/O=$ORG/OU=$OU/CN=PMOVES-DoX-CA" \
    2>/dev/null

# 2. Generate server private key and CSR
log_info "Generating server certificate..."
openssl genrsa -out server.key $KEY_SIZE 2>/dev/null

# Create server extension file for SAN (Subject Alternative Names)
cat > server.ext << EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = nats
DNS.2 = nats.pmoves.local
DNS.3 = localhost
DNS.4 = *.nats.pmoves.local
IP.1 = 127.0.0.1
IP.2 = 0.0.0.0
EOF

openssl req -new -key server.key -out server.csr \
    -subj "/C=$COUNTRY/ST=$STATE/L=$LOCALITY/O=$ORG/OU=$OU/CN=$CN" \
    2>/dev/null

openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key \
    -CAcreateserial -out server.crt -days $DAYS_VALID \
    -extfile server.ext 2>/dev/null

# 3. Generate client certificate (optional, for mTLS)
log_info "Generating client certificate..."
openssl genrsa -out client.key $KEY_SIZE 2>/dev/null

openssl req -new -key client.key -out client.csr \
    -subj "/C=$COUNTRY/ST=$STATE/L=$LOCALITY/O=$ORG/OU=$OU-Client/CN=nats-client" \
    2>/dev/null

cat > client.ext << EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = clientAuth
EOF

openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key \
    -CAcreateserial -out client.crt -days $DAYS_VALID \
    -extfile client.ext 2>/dev/null

# 4. Create combined PEM for clients that need it
cat server.crt server.key > server.pem
cat client.crt client.key > client.pem

# 5. Set permissions
chmod 600 *.key *.pem
chmod 644 *.crt

# Cleanup CSR and extension files
rm -f *.csr *.ext *.srl

log_info "Certificate generation complete!"
echo ""
echo "Generated files:"
echo "  CA Certificate:     $CERT_DIR/ca.crt"
echo "  Server Certificate: $CERT_DIR/server.crt"
echo "  Server Key:         $CERT_DIR/server.key"
echo "  Client Certificate: $CERT_DIR/client.crt"
echo "  Client Key:         $CERT_DIR/client.key"
echo ""
log_warn "For production, use certificates from a trusted CA or Let's Encrypt."
echo ""
echo "To enable TLS in NATS:"
echo "  1. Mount certs volume in docker-compose.yml"
echo "  2. Set NATS_TLS_ENABLED=true"
echo "  3. Restart NATS container"
