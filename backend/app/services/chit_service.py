"""CHIT Geometry Bus service for PMOVES-DoX.

This module provides integration with the NATS Geometry Bus for handling
CHIT Geometry Packets (CGP). It supports both standalone mode (local NATS)
and docked mode (parent PMOVES.AI NATS) with graceful degradation.

ML Embeddings Configuration:
- Set CHIT_USE_LOCAL_EMBEDDINGS=true to enable local SentenceTransformer embeddings
- Embeddings are loaded lazily on first use to minimize startup time
- Falls back to search_index embeddings if local model unavailable
"""

import json
import logging
import asyncio
import os
from typing import Dict, Any, Optional, Callable, List
import nats
from nats.js.api import StreamConfig, RetentionPolicy

# Check for NumPy
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


def _convert_numpy_types(obj: Any) -> Any:
    """Convert numpy types to Python native types for JSON serialization."""
    if HAS_NUMPY:
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.integer, np.int32, np.int64)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float32, np.float64)):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
    if isinstance(obj, dict):
        return {k: _convert_numpy_types(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_convert_numpy_types(item) for item in obj]
    return obj

logger = logging.getLogger(__name__)

# Default model for local embeddings
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Check for SentenceTransformers availability (deferred to avoid opencv GL dependency)
# This is checked lazily when _get_embedding_model() is called


class ChitService:
    """Service to handle CHIT Geometry Packets (CGP) and interface with the NATS Geometry Bus.

    In docked mode (within PMOVES.AI), NATS connection failures are handled gracefully
    since parent NATS may not be available. In standalone mode, NATS is required.

    Attributes:
        nc: NATS connection instance.
        js: JetStream context for NATS.
        model: Optional sentence transformer model for embeddings.
        _nats_available: Whether NATS connection is active.
    """

    def __init__(self) -> None:
        """Initialize the ChitService.

        Creates a new instance with no active NATS connection. Call connect_nats()
        to establish connection to the NATS message bus.
        """
        self.nc = None
        self.js = None
        self._model = None  # Lazy-loaded embedding model
        self._nats_available = False
        self._use_local_embeddings = os.getenv("CHIT_USE_LOCAL_EMBEDDINGS", "").lower() in {"1", "true", "yes"}
        self._embedding_model_name = os.getenv("CHIT_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)

    def _get_embedding_model(self):
        """Lazy-load the SentenceTransformer model on first use.

        Returns:
            SentenceTransformer model instance, or None if unavailable.
        """
        if self._model is not None:
            return self._model

        if not self._use_local_embeddings:
            logger.debug("Local embeddings disabled (set CHIT_USE_LOCAL_EMBEDDINGS=true to enable)")
            return None

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            logger.warning(f"sentence-transformers not available: {e}")
            return None

        try:
            logger.info(f"Loading embedding model: {self._embedding_model_name}")
            self._model = SentenceTransformer(self._embedding_model_name)
            logger.info(f"Embedding model loaded successfully")
            return self._model
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            return None

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts using local model.

        Falls back to empty list if model unavailable. For production use,
        prefer the search_index embeddings from the main application.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors, or empty list if unavailable.
        """
        model = self._get_embedding_model()
        if model is None or not HAS_NUMPY:
            return []

        try:
            embeddings = model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            return []

    @property
    def has_local_embeddings(self) -> bool:
        """Check if local embedding generation is available.

        Returns:
            True if local embeddings can be generated, False otherwise.
        """
        return self._use_local_embeddings and HAS_SENTENCE_TRANSFORMERS

    def _is_docked_mode(self) -> bool:
        """Check if running in docked mode within PMOVES.AI.

        Detection is based on environment variables:
        1. DOCKED_MODE=true (explicit)
        2. NATS_URL=nats://nats:4222 (parent port)

        Returns:
            True if in docked mode, False otherwise.
        """
        # Explicit check first
        if os.getenv("DOCKED_MODE", "").lower() in {"1", "true", "yes"}:
            return True
        # Check NATS URL - parent uses port 4222, standalone uses 4223
        nats_url = os.getenv("NATS_URL", "")
        if nats_url in ("nats://nats:4222", "nats://nats:pmoves@nats:4222"):
            return True
        return False

    async def connect_nats(self, nats_url: str = "nats://nats:pmoves@nats:4222") -> None:
        """Connect to NATS and JetStream.

        In docked mode, connection failures are logged as warnings but don't
        prevent the service from starting (graceful degradation).
        In standalone mode, NATS is required and errors will be raised.

        Args:
            nats_url: NATS server URL (default: "nats://nats:4222").

        Raises:
            Exception: If NATS connection fails in standalone mode.
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

    async def _ensure_stream(self) -> None:
        """Ensure the GEOMETRY JetStream exists.

        Creates the GEOMETRY stream if it doesn't exist. Silently ignores
        errors if the stream already exists.
        """
        if not self.js:
            return

        try:
            await self.js.add_stream(name="GEOMETRY", subjects=["tokenism.cgp.>", "geometry.>"])
            logger.info("Created GEOMETRY stream.")
        except Exception as e:
            # Stream likely exists (e.g., already created by another process)
            logger.debug(f"GEOMETRY stream creation skipped (may already exist): {e}")

    async def subscribe_geometry_events(self, handle_message: Callable) -> None:
        """Subscribe to published CHIT Geometry Packets (CGPs).

        Subscribes to the geometry events on NATS and calls the provided
        handler for each received message. Uses a durable consumer for
        reliable delivery.

        Args:
            handle_message: Async callback function to handle geometry events.
                Will be called with the decoded message data.
        """
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
        """Check if NATS connection is active and available.

        Returns:
            True if NATS is connected and available, False otherwise.
        """
        return self._nats_available and self.nc is not None

    def decode_cgp(self, cgp: Dict[str, Any]) -> Dict[str, Any]:
        """Unpack a CHIT Geometry Packet (CGP) into usable content.

        Extracts text fragments and metadata from the geometry packet structure.
        Logic mirrors chit_decoder.py "exact_decode".

        Args:
            cgp: A CHIT Geometry Packet dictionary containing super_nodes,
                constellations, and points.

        Returns:
            A dictionary with:
            - decoded_items: List of extracted text fragments with metadata
            - raw_cgp: The original CGP for reference
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

    async def publish_cgp(self, cgp: Dict[str, Any], subject: str = "tokenism.cgp.ready.v1") -> bool:
        """Publish a CHIT Geometry Packet to the NATS bus.

        Args:
            cgp: The CHIT Geometry Packet to publish.
            subject: NATS subject to publish to (default: tokenism.cgp.ready.v1).

        Returns:
            True if published successfully, False otherwise.
        """
        if not self._nats_available or not self.nc:
            logger.warning("Cannot publish CGP: NATS not available")
            return False

        try:
            payload = json.dumps(cgp).encode()
            await self.nc.publish(subject, payload)
            logger.info(f"Published CGP to {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish CGP: {e}")
            return False

    async def publish_manifold_update(self, params: Dict[str, Any]) -> bool:
        """Publish a manifold parameter update for real-time visualization.

        Args:
            params: Manifold parameters (curvature_k, epsilon, etc.).

        Returns:
            True if published successfully, False otherwise.
        """
        if not self._nats_available or not self.nc:
            logger.debug("Cannot publish manifold update: NATS not available")
            return False

        try:
            # Convert numpy types to native Python types for JSON serialization
            safe_params = _convert_numpy_types(params)
            payload = json.dumps({
                "type": "manifold_update",
                "parameters": safe_params
            }).encode()
            await self.nc.publish("geometry.event.manifold_update", payload)
            logger.info(f"Published manifold update: curvature_k={safe_params.get('curvature_k')}")
            return True
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize manifold update: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to publish manifold update: {e}")
            return False

    def create_cgp_from_document(
        self,
        document_id: str,
        sections: list,
        curvature_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a CGP from document structure and curvature analysis.

        Args:
            document_id: Document identifier.
            sections: List of document sections with text and metadata.
            curvature_result: Result from GeometryEngine.analyze_curvature().

        Returns:
            A CHIT Geometry Packet dictionary.
        """
        constellations = []

        for i, section in enumerate(sections[:10]):  # Limit to 10 sections
            points = []
            chunks = section.get("chunks", [])

            for j, chunk in enumerate(chunks[:20]):  # Limit to 20 chunks per section
                points.append({
                    "id": f"p_{i}_{j}",
                    "x": (j % 5) * 30 - 60,
                    "y": (j // 5) * 30 - 60,
                    "proj": chunk.get("relevance", 0.5),
                    "conf": chunk.get("confidence", 0.8),
                    "text": chunk.get("text", "")[:100]  # Truncate long text
                })

            if points:
                constellations.append({
                    "id": f"const_{i}",
                    "anchor": [1, 0, 0],
                    "summary": section.get("title", f"Section {i+1}"),
                    "spectrum": [0.5] * 5,
                    "radial_minmax": [0, 1],
                    "points": points
                })

        return {
            "spec": "chit.cgp.v0.1",
            "meta": {
                "source": f"pmoves-dox.document.{document_id}",
                "curvature_k": curvature_result.get("curvature_k", 0),
                "delta": curvature_result.get("delta", 0),
                "epsilon": curvature_result.get("epsilon", 0)
            },
            "super_nodes": [{
                "id": f"doc_{document_id[:8]}",
                "label": f"Document {document_id[:8]}",
                "x": 0,
                "y": 0,
                "r": 200,
                "constellations": constellations
            }]
        }


# Global singleton
chit_service = ChitService()
