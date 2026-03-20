"""Shared NATS TLS context factory for PMOVES-DoX.

Used by both ChitService and IntegrationHealth to ensure consistent
TLS behavior. Fail-closed: raises RuntimeError when TLS is enabled
but context creation fails (never silently degrades to plaintext).
"""

import logging
import os
import re
import ssl
from typing import Optional

logger = logging.getLogger(__name__)


def create_nats_tls_context() -> Optional[ssl.SSLContext]:
    """Create SSL context for NATS TLS connections if enabled.

    Returns:
        SSLContext if NATS_TLS_ENABLED is true, None otherwise.

    Raises:
        RuntimeError: If TLS is enabled but context creation fails
            (fail-closed — never silently degrades to plaintext).
    """
    tls_enabled = os.getenv("NATS_TLS_ENABLED", "").lower() in {"1", "true", "yes"}
    if not tls_enabled:
        return None

    try:
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)

        # Load CA certificate if provided
        ca_file = os.getenv("NATS_TLS_CA", "/app/nats-certs/ca.crt")
        if os.path.exists(ca_file):
            ctx.load_verify_locations(ca_file)
            logger.info(f"Loaded NATS CA certificate from {ca_file}")
        else:
            logger.warning(
                f"NATS CA certificate not found at {ca_file}, "
                "using system default verification"
            )

        # Load client certificate if mutual TLS is configured
        client_cert = os.getenv("NATS_TLS_CERT", "/app/nats-certs/client.crt")
        client_key = os.getenv("NATS_TLS_KEY", "/app/nats-certs/client.key")
        if os.path.exists(client_cert) and os.path.exists(client_key):
            ctx.load_cert_chain(client_cert, client_key)
            logger.info("Loaded NATS client certificate for mutual TLS")

        return ctx
    except Exception as e:
        logger.error(f"Failed to create TLS context: {e}")
        raise RuntimeError(
            f"TLS context creation failed but NATS_TLS_ENABLED=true. "
            f"Fix certificates or disable TLS. Error: {e}"
        ) from e


def sanitize_nats_url(url: str) -> str:
    """Remove credentials from NATS URL for safe logging.

    Example: nats://user:pass@host:4222 -> nats://***@host:4222
    """
    return re.sub(r"://[^@]+@", "://***@", url)
