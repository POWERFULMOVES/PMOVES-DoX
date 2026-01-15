"""Tests for the ChitService (CHIT Geometry Bus integration)."""
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.chit_service import ChitService, chit_service


class TestChitServiceInit:
    """Tests for ChitService initialization."""

    def test_init_sets_defaults(self):
        """New ChitService should have default values."""
        service = ChitService()

        assert service.nc is None
        assert service.js is None
        assert service.model is None
        assert service._nats_available is False

    def test_is_nats_available_property(self):
        """is_nats_available should reflect connection state."""
        service = ChitService()

        # Initially unavailable
        assert service.is_nats_available is False

        # Simulating connection
        service._nats_available = True
        service.nc = MagicMock()
        assert service.is_nats_available is True

        # nc is None
        service.nc = None
        assert service.is_nats_available is False


class TestDockedModeDetection:
    """Tests for _is_docked_mode() detection."""

    def test_explicit_docked_mode_true(self):
        """DOCKED_MODE=true should return True."""
        service = ChitService()

        with patch.dict(os.environ, {"DOCKED_MODE": "true"}):
            assert service._is_docked_mode() is True

        with patch.dict(os.environ, {"DOCKED_MODE": "1"}):
            assert service._is_docked_mode() is True

        with patch.dict(os.environ, {"DOCKED_MODE": "yes"}):
            assert service._is_docked_mode() is True

    def test_explicit_docked_mode_false(self):
        """DOCKED_MODE=false should check NATS_URL."""
        service = ChitService()

        with patch.dict(os.environ, {"DOCKED_MODE": "false", "NATS_URL": ""}, clear=True):
            # Should be False when DOCKED_MODE=false and no parent NATS URL
            assert service._is_docked_mode() is False

    def test_nats_url_parent_port_detection(self):
        """NATS_URL pointing to parent port 4222 indicates docked mode."""
        service = ChitService()

        # Parent NATS URL (port 4222)
        with patch.dict(os.environ, {"DOCKED_MODE": "", "NATS_URL": "nats://nats:4222"}, clear=True):
            assert service._is_docked_mode() is True

        # Standalone NATS URL (port 4223)
        with patch.dict(os.environ, {"DOCKED_MODE": "", "NATS_URL": "nats://nats:4223"}, clear=True):
            assert service._is_docked_mode() is False

    def test_no_env_vars_returns_false(self):
        """No environment variables should default to standalone (False)."""
        service = ChitService()

        with patch.dict(os.environ, {}, clear=True):
            # Remove relevant env vars
            os.environ.pop("DOCKED_MODE", None)
            os.environ.pop("NATS_URL", None)
            assert service._is_docked_mode() is False


class TestDecodeCGP:
    """Tests for ChitService.decode_cgp()."""

    def test_decode_complete_cgp(self):
        """Decoding a complete CGP should extract text fragments."""
        service = ChitService()

        cgp = {
            "spec": "chit.cgp.v0.1",
            "super_nodes": [
                {
                    "id": "sn1",
                    "label": "Test Node",
                    "constellations": [
                        {
                            "id": "c1",
                            "summary": "Test Cluster",
                            "points": [
                                {"id": "p1", "text": "First text", "conf": 0.9},
                                {"id": "p2", "text": "Second text", "conf": 0.8},
                            ]
                        }
                    ]
                }
            ]
        }

        result = service.decode_cgp(cgp)

        assert "decoded_items" in result
        assert "raw_cgp" in result
        assert result["raw_cgp"] == cgp
        assert len(result["decoded_items"]) == 2

        # Check first item
        item = result["decoded_items"][0]
        assert item["type"] == "text_fragment"
        assert item["content"] == "First text"
        assert item["confidence"] == 0.9
        assert item["meta"]["super_node"] == "Test Node"
        assert item["meta"]["constellation"] == "Test Cluster"

    def test_decode_empty_super_nodes(self):
        """Empty super_nodes should return empty decoded_items."""
        service = ChitService()

        cgp = {"spec": "chit.cgp.v0.1", "super_nodes": []}
        result = service.decode_cgp(cgp)

        assert result["decoded_items"] == []
        assert result["raw_cgp"] == cgp

    def test_decode_missing_text_fields(self):
        """Points without text should be skipped."""
        service = ChitService()

        cgp = {
            "super_nodes": [
                {
                    "id": "sn1",
                    "label": "Node",
                    "constellations": [
                        {
                            "id": "c1",
                            "summary": "Cluster",
                            "points": [
                                {"id": "p1", "conf": 0.9},  # No text
                                {"id": "p2", "text": "", "conf": 0.8},  # Empty text
                                {"id": "p3", "text": "Valid", "conf": 0.7},
                            ]
                        }
                    ]
                }
            ]
        }

        result = service.decode_cgp(cgp)

        # Only the point with valid text should be decoded
        assert len(result["decoded_items"]) == 1
        assert result["decoded_items"][0]["content"] == "Valid"

    def test_decode_nested_constellations(self):
        """Multiple constellations in super_node should all be decoded."""
        service = ChitService()

        cgp = {
            "super_nodes": [
                {
                    "id": "sn1",
                    "label": "Node1",
                    "constellations": [
                        {
                            "id": "c1",
                            "summary": "Cluster1",
                            "points": [{"id": "p1", "text": "Text1", "conf": 0.9}]
                        },
                        {
                            "id": "c2",
                            "summary": "Cluster2",
                            "points": [{"id": "p2", "text": "Text2", "conf": 0.8}]
                        }
                    ]
                },
                {
                    "id": "sn2",
                    "label": "Node2",
                    "constellations": [
                        {
                            "id": "c3",
                            "summary": "Cluster3",
                            "points": [{"id": "p3", "text": "Text3", "conf": 0.7}]
                        }
                    ]
                }
            ]
        }

        result = service.decode_cgp(cgp)

        assert len(result["decoded_items"]) == 3
        contents = [item["content"] for item in result["decoded_items"]]
        assert "Text1" in contents
        assert "Text2" in contents
        assert "Text3" in contents

    def test_decode_preserves_confidence(self):
        """Confidence scores should be preserved in decoded items."""
        service = ChitService()

        cgp = {
            "super_nodes": [
                {
                    "id": "sn1",
                    "label": "Node",
                    "constellations": [
                        {
                            "id": "c1",
                            "summary": "Cluster",
                            "points": [
                                {"id": "p1", "text": "High", "conf": 0.95},
                                {"id": "p2", "text": "Low", "conf": 0.1},
                            ]
                        }
                    ]
                }
            ]
        }

        result = service.decode_cgp(cgp)

        high = next(i for i in result["decoded_items"] if i["content"] == "High")
        low = next(i for i in result["decoded_items"] if i["content"] == "Low")

        assert high["confidence"] == 0.95
        assert low["confidence"] == 0.1

    def test_decode_missing_conf_defaults_to_zero(self):
        """Missing conf field should default to 0."""
        service = ChitService()

        cgp = {
            "super_nodes": [
                {
                    "id": "sn1",
                    "constellations": [
                        {
                            "id": "c1",
                            "points": [{"id": "p1", "text": "NoConf"}]
                        }
                    ]
                }
            ]
        }

        result = service.decode_cgp(cgp)

        assert result["decoded_items"][0]["confidence"] == 0


class TestGlobalInstance:
    """Tests for the global chit_service instance."""

    def test_global_instance_exists(self):
        """Global chit_service singleton should exist."""
        assert chit_service is not None
        assert isinstance(chit_service, ChitService)

    def test_global_instance_has_methods(self):
        """Global instance should have expected methods."""
        assert hasattr(chit_service, "connect_nats")
        assert hasattr(chit_service, "decode_cgp")
        assert hasattr(chit_service, "subscribe_geometry_events")
        assert hasattr(chit_service, "is_nats_available")
