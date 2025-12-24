
"""
JWT Generator for Supabase

Utility script to generate signed JWTs (Service Role and Anon) 
for local Supabase development using a pre-defined secret.
"""
import jwt
import time
import secrets

# Simple long string, no base64, no special chars
secret = "this-is-a-very-long-secret-key-for-supabase-local-development-123456789"

# PostgREST config expects simple string if no base64 prefix
# Python jwt.encode will use utf-8 bytes of this string.

service_role_payload = {
    "role": "service_role",
    "iss": "supabase",
    "iat": int(time.time()),
    "exp": int(time.time()) + 3153600000 
}
anon_payload = {
    "role": "anon",
    "iss": "supabase",
    "iat": int(time.time()),
    "exp": int(time.time()) + 3153600000
}

# Sign with string
svc = jwt.encode(service_role_payload, secret, algorithm="HS256")
anon = jwt.encode(anon_payload, secret, algorithm="HS256")

print(f"PGRST_JWT_SECRET={secret}")
print(f"SERVICE_KEY={svc}")
print(f"ANON_KEY={anon}")


