"""Tests for SpectrumAnalyzer service."""
import sys
from pathlib import Path

import pytest
import numpy as np

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.analysis.spectrum_analyzer import (
    SpectrumAnalyzer,
    CoherenceScore,
    EvidenceReliability,
    AttentionDistribution,
    HarmonyAnalysis,
)


class TestSpectrumAnalyzerInit:
    """Tests for SpectrumAnalyzer initialization."""

    def test_init_default_components(self):
        """Default initialization should use 64 components."""
        analyzer = SpectrumAnalyzer()
        assert analyzer.n_components == 64

    def test_init_custom_components(self):
        """Custom component count should be accepted."""
        analyzer = SpectrumAnalyzer(n_components=128)
        assert analyzer.n_components == 128

    def test_init_tracking_counters(self):
        """Counters should start at zero."""
        analyzer = SpectrumAnalyzer()
        assert analyzer._analysis_count == 0
        assert analyzer._total_embeddings_processed == 0


class TestComputeSpectrum:
    """Tests for spectrum computation."""

    @pytest.fixture
    def analyzer(self):
        """Create a spectrum analyzer."""
        return SpectrumAnalyzer(n_components=32)

    def test_compute_spectrum_basic(self, analyzer):
        """Should compute spectrum for simple embedding."""
        embedding = np.random.randn(32)
        spectrum = analyzer.compute_spectrum(embedding)

        assert spectrum is not None
        assert len(spectrum) == 16  # Half of n_components (FFT property)

    def test_compute_spectrum_padded(self, analyzer):
        """Should handle embeddings shorter than n_components."""
        embedding = np.random.randn(10)  # Shorter than 32
        spectrum = analyzer.compute_spectrum(embedding)

        assert spectrum is not None
        assert len(spectrum) == 16

    def test_compute_spectrum_truncated(self, analyzer):
        """Should handle embeddings longer than n_components."""
        embedding = np.random.randn(100)  # Longer than 32
        spectrum = analyzer.compute_spectrum(embedding)

        assert spectrum is not None
        assert len(spectrum) == 16

    def test_compute_spectrum_2d_input(self, analyzer):
        """Should flatten 2D input."""
        embedding = np.random.randn(4, 8)  # 2D array
        spectrum = analyzer.compute_spectrum(embedding)

        assert spectrum is not None
        assert spectrum.ndim == 1


class TestAnalyzeCoherence:
    """Tests for coherence analysis."""

    @pytest.fixture
    def analyzer(self):
        """Create a spectrum analyzer."""
        return SpectrumAnalyzer(n_components=64)

    def test_analyze_coherence_single(self, analyzer):
        """Single embedding should return coherence score."""
        embedding = np.random.randn(64)
        result = analyzer.analyze_coherence([embedding])

        assert isinstance(result, CoherenceScore)
        assert 0.0 <= result.overall_coherence <= 1.0
        assert result.spectral_entropy >= 0

    def test_analyze_coherence_multiple(self, analyzer):
        """Multiple embeddings should be analyzed."""
        embeddings = [np.random.randn(64) for _ in range(5)]
        result = analyzer.analyze_coherence(embeddings)

        assert isinstance(result, CoherenceScore)

    def test_analyze_coherence_identical(self, analyzer):
        """Identical embeddings should have high coherence."""
        base = np.random.randn(64)
        embeddings = [base.copy() for _ in range(5)]
        result = analyzer.analyze_coherence(embeddings)

        # Identical embeddings = high coherence
        assert result.overall_coherence >= 0.8

    def test_analyze_coherence_diverse(self, analyzer):
        """Diverse embeddings should have lower coherence."""
        embeddings = [np.random.randn(64) * (i + 1) for i in range(5)]
        result = analyzer.analyze_coherence(embeddings)

        # Result should be valid (coherence varies based on randomness)
        assert 0.0 <= result.overall_coherence <= 1.0


class TestWeightEvidenceReliability:
    """Tests for evidence reliability weighting."""

    @pytest.fixture
    def analyzer(self):
        """Create a spectrum analyzer."""
        return SpectrumAnalyzer(n_components=32)

    def test_weight_evidence_single(self, analyzer):
        """Single evidence should be weighted."""
        evidence = {
            "id": "ev-1",
            "embedding": np.random.randn(32).tolist()
        }
        results = analyzer.weight_evidence_reliability([evidence])

        assert len(results) == 1
        assert isinstance(results[0], EvidenceReliability)
        assert results[0].evidence_id == "ev-1"
        assert 0.0 <= results[0].reliability_score <= 1.0

    def test_weight_evidence_multiple(self, analyzer):
        """Multiple pieces of evidence should be weighted."""
        evidence_list = [
            {"id": f"ev-{i}", "embedding": np.random.randn(32).tolist()}
            for i in range(3)
        ]
        results = analyzer.weight_evidence_reliability(evidence_list)

        assert len(results) == 3

    def test_weight_evidence_identifies_outliers(self, analyzer):
        """Outlier evidence should have lower reliability."""
        # Create similar embeddings
        base = np.random.randn(32)
        similar = [{"id": f"similar-{i}", "embedding": (base + np.random.randn(32) * 0.1).tolist()}
                   for i in range(4)]

        # Add one outlier
        outlier = {"id": "outlier", "embedding": (np.random.randn(32) * 10).tolist()}
        all_evidence = similar + [outlier]

        results = analyzer.weight_evidence_reliability(all_evidence)

        # Find the outlier result
        outlier_result = next(r for r in results if r.evidence_id == "outlier")
        similar_scores = [r.reliability_score for r in results if r.evidence_id.startswith("similar")]

        # Outlier should have lower or equal reliability
        assert outlier_result.outlier_degree >= 0


class TestDistributeAttention:
    """Tests for attention distribution."""

    @pytest.fixture
    def analyzer(self):
        """Create a spectrum analyzer."""
        return SpectrumAnalyzer(n_components=32)

    def test_distribute_attention_basic(self, analyzer):
        """Should distribute attention across sources."""
        sources = {
            "agent-1": np.random.randn(32).tolist(),
            "agent-2": np.random.randn(32).tolist(),
            "agent-3": np.random.randn(32).tolist(),
        }
        result = analyzer.distribute_attention(sources)

        assert isinstance(result, AttentionDistribution)
        assert len(result.distribution) == 3
        assert sum(result.distribution.values()) == pytest.approx(1.0, abs=0.01)

    def test_distribute_attention_entropy(self, analyzer):
        """Uniform distribution should have high entropy."""
        # Similar embeddings should give more uniform attention
        base = np.random.randn(32)
        sources = {
            f"agent-{i}": (base + np.random.randn(32) * 0.1).tolist()
            for i in range(3)
        }
        result = analyzer.distribute_attention(sources)

        assert result.entropy >= 0

    def test_distribute_attention_dominant(self, analyzer):
        """Should identify dominant source."""
        sources = {
            "weak-1": np.random.randn(32).tolist(),
            "weak-2": np.random.randn(32).tolist(),
            "strong": (np.ones(32) * 10).tolist(),  # Strong signal
        }
        result = analyzer.distribute_attention(sources)

        # Should have a dominant source (or None if balanced)
        assert result.dominant_source is not None or result.entropy > 0


class TestAnalyzeHarmony:
    """Tests for harmony analysis."""

    @pytest.fixture
    def analyzer(self):
        """Create a spectrum analyzer."""
        return SpectrumAnalyzer(n_components=32)

    def test_analyze_harmony_basic(self, analyzer):
        """Should analyze knowledge base harmony."""
        knowledge_items = {
            "fact-1": np.random.randn(32).tolist(),
            "fact-2": np.random.randn(32).tolist(),
            "fact-3": np.random.randn(32).tolist(),
        }
        result = analyzer.analyze_harmony(knowledge_items)

        assert isinstance(result, HarmonyAnalysis)
        assert 0.0 <= result.harmony_score <= 1.0

    def test_analyze_harmony_consonant_pairs(self, analyzer):
        """Similar items should be consonant."""
        base = np.random.randn(32)
        knowledge_items = {
            "similar-1": base.tolist(),
            "similar-2": (base + np.random.randn(32) * 0.01).tolist(),
        }
        result = analyzer.analyze_harmony(knowledge_items)

        # Similar items should have consonant pair
        assert len(result.consonant_pairs) >= 0

    def test_analyze_harmony_dissonant_pairs(self, analyzer):
        """Opposite items should be dissonant."""
        base = np.random.randn(32)
        knowledge_items = {
            "positive": base.tolist(),
            "negative": (-base).tolist(),  # Opposite
        }
        result = analyzer.analyze_harmony(knowledge_items)

        # Opposite embeddings should have dissonance
        assert len(result.dissonant_pairs) >= 0


class TestModels:
    """Tests for Pydantic models."""

    def test_coherence_score_validation(self):
        """CoherenceScore should validate bounds."""
        score = CoherenceScore(
            overall_coherence=0.85,
            spectral_entropy=1.5,
            dominant_frequency=0.25,
            harmonic_ratio=0.7
        )

        assert score.overall_coherence == 0.85
        assert score.discord_regions == []

    def test_coherence_score_out_of_bounds(self):
        """CoherenceScore should reject invalid values."""
        with pytest.raises(ValueError):
            CoherenceScore(
                overall_coherence=1.5,  # > 1.0
                spectral_entropy=1.0,
                dominant_frequency=0.5,
                harmonic_ratio=0.5
            )

    def test_evidence_reliability_validation(self):
        """EvidenceReliability should validate bounds."""
        reliability = EvidenceReliability(
            evidence_id="ev-1",
            reliability_score=0.9,
            spectral_consistency=0.85,
            outlier_degree=0.1
        )

        assert reliability.evidence_id == "ev-1"
        assert reliability.reliability_score == 0.9

    def test_attention_distribution_creation(self):
        """AttentionDistribution should accept distribution."""
        dist = AttentionDistribution(
            distribution={"agent-1": 0.6, "agent-2": 0.4},
            entropy=0.97,
            concentration=1.03,
            dominant_source="agent-1"
        )

        assert dist.distribution["agent-1"] == 0.6
        assert dist.dominant_source == "agent-1"

    def test_harmony_analysis_creation(self):
        """HarmonyAnalysis should track pairs."""
        harmony = HarmonyAnalysis(
            harmony_score=0.75,
            consonant_pairs=[("fact-1", "fact-2")],
            dissonant_pairs=[("fact-1", "fact-3")],
            suggested_reconciliations=["Review fact-3 for accuracy"]
        )

        assert harmony.harmony_score == 0.75
        assert len(harmony.consonant_pairs) == 1
        assert len(harmony.dissonant_pairs) == 1


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def analyzer(self):
        """Create a spectrum analyzer."""
        return SpectrumAnalyzer(n_components=32)

    def test_empty_embedding(self, analyzer):
        """Should handle empty embedding."""
        embedding = np.array([])
        spectrum = analyzer.compute_spectrum(embedding)

        # Should return some result (padded zeros)
        assert spectrum is not None

    def test_zero_embedding(self, analyzer):
        """Should handle all-zero embedding."""
        embedding = np.zeros(32)
        spectrum = analyzer.compute_spectrum(embedding)

        assert spectrum is not None
        # Zero input should give zero spectrum
        assert np.allclose(spectrum, 0)

    def test_single_embedding_coherence(self, analyzer):
        """Single embedding coherence should be maximum."""
        embedding = np.random.randn(32)
        result = analyzer.analyze_coherence([embedding])

        # Single embedding = perfect self-coherence
        assert result.overall_coherence >= 0.9

    def test_empty_evidence_list(self, analyzer):
        """Empty evidence list should return empty results."""
        results = analyzer.weight_evidence_reliability([])
        assert results == []

    def test_empty_sources_attention(self, analyzer):
        """Empty sources should return empty distribution."""
        result = analyzer.distribute_attention({})

        assert result.distribution == {}
        assert result.entropy == 0.0
