
import json
import logging
import asyncio
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
    """
    
    def __init__(self):
        self.nc = None
        self.js = None
        self.model = None
        
        # Load embedding model lazily if needed for geometry-only decoding
        if HAS_ML:
             # self.model = SentenceTransformer('all-MiniLM-L6-v2') 
             pass

    async def connect_nats(self, nats_url: str = "nats://nats:4222"):
        """Connect to NATS and JetStream."""
        try:
            self.nc = await nats.connect(nats_url)
            self.js = self.nc.jetstream()
            logger.info(f"Connected to NATS at {nats_url}")
            
            # Ensure the stream exists
            # We want a 'geometry' stream capturing all geometry events
            await self._ensure_stream()
            
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")

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
        if not self.js: 
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
        await self.js.subscribe("tokenism.cgp.ready.v1", cb=cb, durable="dox-geometry-consumer")

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
