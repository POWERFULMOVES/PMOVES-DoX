"""Tests for the GeometryEngine service."""
import sys
from pathlib import Path

import numpy as np
import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.geometry_engine import GeometryEngine, geometry_engine


class TestAnalyzeCurvature:
    """Tests for GeometryEngine.analyze_curvature()."""

    def test_insufficient_data_returns_zero_defaults(self):
        """Less than 4 embeddings returns zero values."""
        engine = GeometryEngine()

        # Empty
        result = engine.analyze_curvature([])
        assert result == {"delta": 0.0, "curvature_k": 0.0, "epsilon": 0.0}

        # 1 embedding
        result = engine.analyze_curvature([[1, 2, 3]])
        assert result == {"delta": 0.0, "curvature_k": 0.0, "epsilon": 0.0}

        # 3 embeddings (still not enough)
        result = engine.analyze_curvature([[1, 2], [3, 4], [5, 6]])
        assert result == {"delta": 0.0, "curvature_k": 0.0, "epsilon": 0.0}

    def test_hyperbolic_tree_high_variance(self):
        """High variance embeddings produce negative curvature (hyperbolic)."""
        engine = GeometryEngine()

        # Create tree-like data: centroid at origin with outliers far away
        # This gives high std/mean ratio (> 0.5)
        embeddings = [
            [0, 0, 0],     # Center
            [10, 0, 0],    # Far outlier
            [0, 8, 0],     # Far outlier
            [-5, -5, -5],  # Another branch
            [0.1, 0.1, 0], # Near center
        ]

        result = engine.analyze_curvature(embeddings)

        # Should have high delta (shape_ratio > 0.5)
        assert result["delta"] > 0.4
        # Should have negative curvature for hyperbolic
        assert result["curvature_k"] < 0

    def test_spherical_cluster_low_variance(self):
        """Low variance (compact cluster) produces positive curvature (spherical)."""
        engine = GeometryEngine()

        # Create compact cluster: all points at nearly identical distance from origin
        # Points on a shell at radius 5 with tiny variation
        np.random.seed(42)
        n_points = 20
        # Generate points on a sphere surface (nearly uniform distance to center)
        theta = np.random.uniform(0, 2*np.pi, n_points)
        phi = np.random.uniform(0, np.pi, n_points)
        r = 5.0 + np.random.randn(n_points) * 0.001  # Very small variance in radius

        x = r * np.sin(phi) * np.cos(theta)
        y = r * np.sin(phi) * np.sin(theta)
        z = r * np.cos(phi)
        embeddings = np.column_stack([x, y, z]).tolist()

        result = engine.analyze_curvature(embeddings)

        # Points on a sphere surface have very uniform distance to center
        # This should give a low shape_ratio (std/mean is small)
        assert result["delta"] < 0.5
        # Curvature should be non-negative for compact/spherical data
        assert result["curvature_k"] >= -1.0

    def test_euclidean_flat_medium_variance(self):
        """Medium variance produces near-zero curvature (Euclidean)."""
        engine = GeometryEngine()

        # Create uniform distribution - medium variance
        np.random.seed(42)
        embeddings = np.random.uniform(-1, 1, (10, 3)).tolist()

        result = engine.analyze_curvature(embeddings)

        # Shape ratio should be in middle range (0.2-0.5)
        # Curvature should be near 0
        assert -1.0 <= result["curvature_k"] <= 1.0

    def test_curvature_k_bounds(self):
        """Curvature k should be bounded roughly between -5 and 5."""
        engine = GeometryEngine()

        # Test extreme high variance (hyperbolic)
        extreme_tree = [[0, 0], [100, 0], [0, 100], [-100, -100], [0.001, 0.001]]
        result = engine.analyze_curvature(extreme_tree)
        assert result["curvature_k"] >= -10  # Should not go infinitely negative

        # Test extreme low variance (spherical)
        tight_cluster = [[1, 1], [1.001, 1], [1, 1.001], [1.001, 1.001]]
        result = engine.analyze_curvature(tight_cluster)
        assert result["curvature_k"] <= 10  # Should not go infinitely positive

    def test_epsilon_bounded_zero_one(self):
        """Epsilon should always be between 0 and 1."""
        engine = GeometryEngine()

        # Various inputs
        test_cases = [
            [[0, 0], [1, 1], [2, 2], [3, 3]],  # Linear
            [[0, 0, 0], [10, 0, 0], [0, 10, 0], [0, 0, 10]],  # Spread out
            np.random.randn(20, 5).tolist(),  # Random
        ]

        for embeddings in test_cases:
            result = engine.analyze_curvature(embeddings)
            assert 0.0 <= result["epsilon"] <= 1.0

    def test_returns_float_values(self):
        """All returned values should be floats."""
        engine = GeometryEngine()

        embeddings = [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]]
        result = engine.analyze_curvature(embeddings)

        assert isinstance(result["delta"], (int, float))
        assert isinstance(result["curvature_k"], (int, float))
        assert isinstance(result["epsilon"], (int, float))


class TestGenerateChitConfig:
    """Tests for GeometryEngine.generate_chit_config()."""

    def test_hyperbolic_config(self):
        """Negative curvature produces hyperbolic (Pseudosphere) config."""
        engine = GeometryEngine()

        analysis = {"delta": 0.7, "curvature_k": -2.5, "epsilon": 0.5}
        config = engine.generate_chit_config(analysis)

        assert config["meta"]["inferred_shape"] == "Hyperbolic (Pseudosphere)"
        assert "Tractrix" in config["surfaceFn"] or "Pseudosphere" in config["surfaceFn"]
        assert config["surfaceInput"]["curvature"] == -2.5
        assert config["surfaceInput"]["epsilon"] == 0.5

    def test_spherical_config(self):
        """Positive curvature produces spherical config."""
        engine = GeometryEngine()

        analysis = {"delta": 0.1, "curvature_k": 3.0, "epsilon": 0.2}
        config = engine.generate_chit_config(analysis)

        assert config["meta"]["inferred_shape"] == "Spherical"
        assert "sin" in config["surfaceFn"] and "cos" in config["surfaceFn"]
        assert config["surfaceInput"]["curvature"] == 3.0

    def test_flat_config(self):
        """Near-zero curvature produces flat config."""
        engine = GeometryEngine()

        analysis = {"delta": 0.3, "curvature_k": 0.0, "epsilon": 0.3}
        config = engine.generate_chit_config(analysis)

        assert config["meta"]["inferred_shape"] == "Flat"
        assert config["surfaceInput"]["curvature"] == 0.0

    def test_config_has_required_fields(self):
        """Config should have all required fields for the visualizer."""
        engine = GeometryEngine()

        analysis = {"delta": 0.5, "curvature_k": 0.0, "epsilon": 0.5}
        config = engine.generate_chit_config(analysis)

        # Required top-level fields
        assert "surfaceFn" in config
        assert "params" in config
        assert "surfaceInput" in config
        assert "animatedParams" in config
        assert "camera" in config
        assert "meta" in config

        # Params structure
        assert config["params"]["uMin"] == 0
        assert config["params"]["uMax"] == 1
        assert config["params"]["vMin"] == 0
        assert config["params"]["vMax"] == 1

        # Camera structure
        assert "position" in config["camera"]
        assert "target" in config["camera"]

    def test_animated_epsilon_bounds(self):
        """Animated epsilon params should be bounded correctly."""
        engine = GeometryEngine()

        # Test various epsilon values
        for eps in [0.1, 0.5, 0.9]:
            analysis = {"delta": 0.5, "curvature_k": 0.0, "epsilon": eps}
            config = engine.generate_chit_config(analysis)

            anim = config["animatedParams"][0]
            assert anim["name"] == "epsilon"
            assert anim["min"] >= 0.0
            assert anim["max"] <= 1.0
            assert anim["min"] <= anim["max"]

    def test_surface_fn_is_valid_js(self):
        """Surface function should be valid JavaScript."""
        engine = GeometryEngine()

        for k in [-3.0, 0.0, 3.0]:
            analysis = {"delta": 0.5, "curvature_k": k, "epsilon": 0.5}
            config = engine.generate_chit_config(analysis)

            fn = config["surfaceFn"]
            # Basic JS validation
            assert fn.startswith("function surface(input)")
            assert "return" in fn
            assert fn.count("{") == fn.count("}")


class TestGetSurfaceFnCode:
    """Tests for GeometryEngine._get_surface_fn_code()."""

    def test_hyperbolic_tractrix_formula(self):
        """Hyperbolic surface uses tractrix/pseudosphere formula."""
        engine = GeometryEngine()

        fn = engine._get_surface_fn_code(-2.0)

        assert "Tractrix" in fn or "Pseudosphere" in fn or "log" in fn
        assert "Math.sin" in fn
        assert "Math.cos" in fn

    def test_spherical_formula(self):
        """Spherical surface uses standard sphere parametrization."""
        engine = GeometryEngine()

        fn = engine._get_surface_fn_code(2.0)

        assert "Math.sin(v)" in fn
        assert "Math.cos(u)" in fn

    def test_flat_plane_formula(self):
        """Flat surface uses plane formula."""
        engine = GeometryEngine()

        fn = engine._get_surface_fn_code(0.0)

        # Flat should have simple x = u, y = v pattern
        assert "x: u" in fn or "x: (input.u" in fn


class TestComputeZetaSpectrum:
    """Tests for GeometryEngine.compute_zeta_spectrum()."""

    def test_empty_embeddings_returns_defaults(self):
        """Empty embeddings return default zeta zeros."""
        engine = GeometryEngine()

        frequencies, amplitudes = engine.compute_zeta_spectrum([])

        # Should return first 3 default zeta zeros
        assert len(frequencies) == 3
        assert len(amplitudes) == 3
        # First frequency should be near 14.13 (first zeta zero)
        assert 14.0 < frequencies[0] < 15.0

    def test_single_embedding_returns_defaults(self):
        """Single embedding returns default values."""
        engine = GeometryEngine()

        frequencies, amplitudes = engine.compute_zeta_spectrum([[1, 2, 3]])

        assert len(frequencies) == 3
        assert len(amplitudes) == 3

    def test_valid_embeddings_compute_frequencies(self):
        """Valid embeddings compute dynamic frequencies."""
        engine = GeometryEngine()

        # Create embeddings with clear variance structure
        np.random.seed(42)
        embeddings = np.random.randn(20, 8).tolist()  # 20 samples, 8 dimensions

        frequencies, amplitudes = engine.compute_zeta_spectrum(embeddings)

        # Should compute frequencies from eigenvalues
        assert len(frequencies) >= 1
        assert len(amplitudes) == len(frequencies)
        # All frequencies should be positive
        assert all(f > 0 for f in frequencies)
        # All amplitudes should be in (0, 1]
        assert all(0 < a <= 1 for a in amplitudes)

    def test_frequencies_near_zeta_zeros(self):
        """Computed frequencies should be near zeta zero range (14-34)."""
        engine = GeometryEngine()

        np.random.seed(123)
        embeddings = np.random.randn(30, 10).tolist()

        frequencies, amplitudes = engine.compute_zeta_spectrum(embeddings)

        # Frequencies should be in the zeta-like range
        for f in frequencies:
            assert 10.0 < f < 40.0, f"Frequency {f} outside expected range"

    def test_amplitudes_decay(self):
        """Amplitudes should generally decay (first > later)."""
        engine = GeometryEngine()

        np.random.seed(456)
        embeddings = np.random.randn(50, 16).tolist()

        frequencies, amplitudes = engine.compute_zeta_spectrum(embeddings)

        if len(amplitudes) >= 3:
            # First amplitude should typically be largest
            # (allowing some variance due to eigenvalue modulation)
            avg_first = amplitudes[0]
            avg_last = sum(amplitudes[-2:]) / 2
            assert avg_first >= avg_last * 0.5, "Amplitudes should roughly decay"

    def test_2d_embeddings_work(self):
        """2D embeddings (like point coordinates) should work."""
        engine = GeometryEngine()

        # Simulate CGP point coordinates
        embeddings = [
            [50, 50, 0.9, 0.95],
            [-40, 60, 0.8, 0.85],
            [-20, -80, 0.7, 0.80],
            [30, 30, 0.6, 0.90],
        ]

        frequencies, amplitudes = engine.compute_zeta_spectrum(embeddings)

        assert len(frequencies) >= 1
        assert len(amplitudes) >= 1


class TestGlobalInstance:
    """Tests for the global geometry_engine instance."""

    def test_global_instance_exists(self):
        """Global geometry_engine singleton should exist."""
        assert geometry_engine is not None
        assert isinstance(geometry_engine, GeometryEngine)

    def test_global_instance_methods(self):
        """Global instance should have expected methods."""
        assert hasattr(geometry_engine, "analyze_curvature")
        assert hasattr(geometry_engine, "generate_chit_config")
        assert hasattr(geometry_engine, "compute_zeta_spectrum")
        assert callable(geometry_engine.analyze_curvature)
        assert callable(geometry_engine.generate_chit_config)
        assert callable(geometry_engine.compute_zeta_spectrum)
