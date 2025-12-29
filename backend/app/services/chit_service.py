
import json
import logging
import asyncio
import os
from typing import Dict, Any, Optional
import nats
from nats.js.api import StreamConfig, RetentionPolicy

# Attempt to import NLP/ML libraries, but fail gracefully if not installed
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    import faiss
    HAS_ML = True
except ImportError:
    HAS_ML = False

logger = logging.getLogger(__name__)

class ChitService:
    """
    Service to handle CHIT Geomerty Packets (CGP) and interface with the NATS Geometry Bus.

    In docked mode (within PMOVES.AI), NATS connection failures are handled gracefully
    since parent NATS may not be available. In standalone mode, NATS is required.
    """

    def __init__(self):
        self.nc = None
        self.js = None
        self.model = None
        self._nats_available = False

        # Load embedding model lazily if needed for geometry-only decoding
        if HAS_ML:
             # self.model = SentenceTransformer('all-MiniLM-L6-v2')
             pass

    def _is_docked_mode(self) -> bool:
        """Check if running in docked mode within PMOVES.AI."""
        # Explicit check first
        if os.getenv("DOCKED_MODE", "").lower() in {"1", "true", "yes"}:
            return True
        # Check NATS URL - parent uses port 4222, standalone uses 4223
        nats_url = os.getenv("NATS_URL", "")
        if nats_url == "nats://nats:4222":
            return True
        return False

    async def connect_nats(self, nats_url: str = "nats://nats:4222"):
        """Connect to NATS and JetStream.

        In docked mode, connection failures are logged as warnings but don't
        prevent the service from starting (graceful degradation).
        In standalone mode, NATS is required and errors should be surfaced.
        """
        try:
            self.nc = await nats.connect(nats_url)
            self.js = self.nc.jetstream()
            self._nats_available = True
            logger.info(f"Connected to NATS at {nats_url}")

            # Ensure the stream exists
            # We want a 'geometry' stream capturing all geometry events
            await self._ensure_stream()

        except Exception as e:
            self._nats_available = False
            is_docked = self._is_docked_mode()
            if is_docked:
                # Graceful degradation in docked mode
                logger.warning(f"NATS connection failed (docked mode, continuing anyway): {e}")
                logger.warning("Geometry bus features will be disabled")
            else:
                # In standalone mode, NATS is expected to be available
                logger.error(f"Failed to connect to NATS (standalone mode): {e}")
                # Re-raise in standalone mode so admin knows NATS is required
                raise

    async def _ensure_stream(self):
        if not self.js: return
        
        try:
            await self.js.add_stream(name="GEOMETRY", subjects=["tokenism.cgp.>", "geometry.>"])
            logger.info("Created GEOMETRY stream.")
        except Exception as e:
            # Stream likely exists
            pass

    async def subscribe_geometry_events(self, handle_message):
        """Subscribe to published CGPs."""
        if not self.js or not self._nats_available:
            if self._is_docked_mode():
                logger.debug("NATS not available in docked mode, skipping geometry subscription")
            else:
                logger.warning("NATS not connected, cannot subscribe.")
            return

        async def cb(msg):
            try:
                data = json.loads(msg.data.decode())
                subject = msg.subject
                logger.info(f"Received geometry event on {subject}")
                await handle_message(data)
                await msg.ack()
            except Exception as e:
                logger.error(f"Error handling geometry msg: {e}")

        # Durable consumer for reliable delivery
        try:
            await self.js.subscribe("tokenism.cgp.ready.v1", cb=cb, durable="dox-geometry-consumer")
        except Exception as e:
            logger.warning(f"Failed to subscribe to geometry events: {e}")

    @property
    def is_nats_available(self) -> bool:
        """Check if NATS connection is active and available."""
        return self._nats_available and self.nc is not None

    def decode_cgp(self, cgp: Dict[str, Any]) -> Dict[str, Any]:
        """
        Unpack a CGP into usable content.
        logic mirrors chit_decoder.py "exact_decode".
        """
        results = []
        
        super_nodes = cgp.get("super_nodes", [])
        for sn in super_nodes:
            for const in sn.get("constellations", []):
                for pt in const.get("points", []):
                    # Check for explicit text
                    if "text" in pt and pt["text"]:
                        results.append({
                            "type": "text_fragment",
                            "content": pt["text"],
                            "confidence": pt.get("conf", 0),
                            "meta": {
                                "super_node": sn.get("label"),
                                "constellation": const.get("summary")
                            }
                        })
                        
        return {
            "decoded_items": results,
            "raw_cgp": cgp
        }

# Global singleton
chit_service = ChitService()
