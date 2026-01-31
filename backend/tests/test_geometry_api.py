"""Tests for the geometry API endpoints (/cipher/geometry/*)."""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


class TestDemoPacketEndpoint:
    """Tests for GET /cipher/geometry/demo-packet."""

    def test_returns_valid_cgp(self):
        """Endpoint should return valid CGP structure."""
        response = client.get("/cipher/geometry/demo-packet")

        assert response.status_code == 200
        data = response.json()

        # Verify CGP spec
        assert data.get("spec") == "chit.cgp.v0.1"
        assert "super_nodes" in data
        assert isinstance(data["super_nodes"], list)

    def test_has_required_fields(self):
        """CGP should have all required fields."""
        response = client.get("/cipher/geometry/demo-packet")
        data = response.json()

        # Top-level
        assert "spec" in data
        assert "meta" in data
        assert "super_nodes" in data

        # Super node structure
        if data["super_nodes"]:
            sn = data["super_nodes"][0]
            assert "id" in sn
            assert "x" in sn
            assert "y" in sn
            assert "r" in sn
            assert "label" in sn
            assert "constellations" in sn

    def test_constellations_have_points(self):
        """Constellations should contain points with text."""
        response = client.get("/cipher/geometry/demo-packet")
        data = response.json()

        # Find first constellation with points
        for sn in data["super_nodes"]:
            for const in sn.get("constellations", []):
                assert "id" in const
                assert "summary" in const
                assert "points" in const

                # Verify point structure
                for pt in const["points"]:
                    assert "id" in pt
                    assert "x" in pt
                    assert "y" in pt


class TestSimulateEndpoint:
    """Tests for POST /cipher/geometry/simulate."""

    def test_accepts_valid_cgp(self):
        """Endpoint should accept valid CGP and return A2UI response."""
        cgp = {
            "spec": "chit.cgp.v0.1",
            "super_nodes": [
                {
                    "id": "test",
                    "x": 0, "y": 0, "r": 100,
                    "label": "Test Node",
                    "constellations": []
                }
            ]
        }

        response = client.post("/cipher/geometry/simulate", json=cgp)

        assert response.status_code == 200
        data = response.json()
        assert "surfaceUpdate" in data

    def test_returns_a2ui_format(self):
        """Response should follow A2UI surface update format."""
        cgp = {
            "spec": "chit.cgp.v0.1",
            "super_nodes": []
        }

        response = client.post("/cipher/geometry/simulate", json=cgp)
        data = response.json()

        # A2UI structure
        assert "surfaceUpdate" in data
        surface = data["surfaceUpdate"]
        assert "surfaceId" in surface
        assert "components" in surface
        assert isinstance(surface["components"], list)

        # Should have beginRendering
        assert "beginRendering" in data

    def test_includes_hyperbolic_navigator(self):
        """Response should include HyperbolicNavigator component."""
        cgp = {
            "spec": "chit.cgp.v0.1",
            "super_nodes": [{"id": "test", "x": 0, "y": 0, "r": 50, "label": "Test", "constellations": []}]
        }

        response = client.post("/cipher/geometry/simulate", json=cgp)
        data = response.json()

        components = data["surfaceUpdate"]["components"]
        navigator_found = any(
            "HyperbolicNavigator" in str(c.get("component", {}))
            for c in components
        )
        assert navigator_found, "HyperbolicNavigator component not found"

    def test_includes_zeta_visualizer(self):
        """Response should include ZetaVisualizer component."""
        cgp = {
            "spec": "chit.cgp.v0.1",
            "super_nodes": []
        }

        response = client.post("/cipher/geometry/simulate", json=cgp)
        data = response.json()

        components = data["surfaceUpdate"]["components"]
        zeta_found = any(
            "ZetaVisualizer" in str(c.get("component", {}))
            for c in components
        )
        assert zeta_found, "ZetaVisualizer component not found"

    def test_zeta_has_frequencies_and_amplitudes(self):
        """ZetaVisualizer should have frequencies and amplitudes arrays."""
        cgp = {"spec": "chit.cgp.v0.1", "super_nodes": []}

        response = client.post("/cipher/geometry/simulate", json=cgp)
        data = response.json()

        for comp in data["surfaceUpdate"]["components"]:
            zeta = comp.get("component", {}).get("ZetaVisualizer")
            if zeta:
                assert "frequencies" in zeta
                assert "amplitudes" in zeta
                assert isinstance(zeta["frequencies"], list)
                assert isinstance(zeta["amplitudes"], list)
                assert len(zeta["frequencies"]) > 0


class TestVisualizeManifoldEndpoint:
    """Tests for POST /cipher/geometry/visualize_manifold."""

    def test_demo_mode(self):
        """Demo mode (document_id='demo') should return valid response."""
        response = client.post(
            "/cipher/geometry/visualize_manifold",
            json={"document_id": "demo"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"

    def test_returns_metrics(self):
        """Response should include curvature metrics."""
        response = client.post(
            "/cipher/geometry/visualize_manifold",
            json={"document_id": "demo"}
        )

        data = response.json()
        assert "metrics" in data

        metrics = data["metrics"]
        assert "delta" in metrics
        assert "curvature_k" in metrics
        assert "epsilon" in metrics

    def test_returns_shape_classification(self):
        """Response should include shape classification."""
        response = client.post(
            "/cipher/geometry/visualize_manifold",
            json={"document_id": "demo"}
        )

        data = response.json()
        assert "shape" in data
        assert data["shape"] in ["Flat", "Hyperbolic (Pseudosphere)", "Spherical"]

    def test_returns_visualization_url(self):
        """Response should include URL to visualization."""
        response = client.post(
            "/cipher/geometry/visualize_manifold",
            json={"document_id": "demo"}
        )

        data = response.json()
        assert "url" in data
        assert "hyperdimensions" in data["url"]
        assert "chit_manifold.json" in data["url"]


class TestSkillsEndpoints:
    """Tests for cipher skills endpoints (requires database)."""

    def test_list_skills(self):
        """GET /cipher/skills should return skills list."""
        try:
            response = client.get("/cipher/skills")
        except Exception as e:
            pytest.skip(f"Database not properly configured: {e}")

        # May fail with 500 if database not configured (Supabase JWT issues)
        if response.status_code == 500:
            pytest.skip("Database not properly configured for skills endpoint")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_memory_endpoint_exists(self):
        """Memory endpoints should exist."""
        try:
            response = client.get("/cipher/memory")
        except Exception as e:
            pytest.skip(f"Database not properly configured: {e}")

        # May fail with 500 if database not configured
        if response.status_code == 500:
            pytest.skip("Database not properly configured for memory endpoint")

        assert response.status_code in [200, 404]  # May not have data


class TestGeometryResponseSchemas:
    """Tests for API response schema validation."""

    def test_demo_packet_json_serializable(self):
        """Demo packet should be fully JSON serializable."""
        import json

        response = client.get("/cipher/geometry/demo-packet")
        # If response is valid, it's already serializable
        assert response.status_code == 200

        # Double-check by re-serializing
        data = response.json()
        serialized = json.dumps(data)
        assert serialized is not None

    def test_simulate_response_consistent(self):
        """Simulate should return consistent structure for different inputs."""
        # Minimal input
        r1 = client.post("/cipher/geometry/simulate", json={
            "spec": "chit.cgp.v0.1", "super_nodes": []
        })

        # With data
        r2 = client.post("/cipher/geometry/simulate", json={
            "spec": "chit.cgp.v0.1",
            "super_nodes": [{"id": "a", "x": 0, "y": 0, "r": 10, "label": "A", "constellations": []}]
        })

        # Both should have same top-level structure
        d1 = r1.json()
        d2 = r2.json()

        assert set(d1.keys()) == set(d2.keys())
        assert "surfaceUpdate" in d1
        assert "surfaceUpdate" in d2
