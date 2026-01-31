"""Spectrum analyzer for embedding spectral analysis.

This module analyzes the spectral properties of embeddings for:
- Content coherence scoring
- Evidence reliability weighting
- Agent attention distribution
- Knowledge base harmony/discord detection

Based on Riemann Zeta spectral patterns from the geometry engine.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CoherenceScore(BaseModel):
    """Coherence analysis result."""

    overall_coherence: float = Field(ge=0.0, le=1.0)
    spectral_entropy: float
    dominant_frequency: float
    harmonic_ratio: float
    discord_regions: List[Tuple[int, int]] = Field(default_factory=list)


class EvidenceReliability(BaseModel):
    """Evidence reliability based on spectral analysis."""

    evidence_id: str
    reliability_score: float = Field(ge=0.0, le=1.0)
    spectral_consistency: float
    outlier_degree: float


class AttentionDistribution(BaseModel):
    """Attention distribution across agents/sources."""

    distribution: Dict[str, float]
    entropy: float
    concentration: float  # Inverse of entropy, higher = more focused
    dominant_source: Optional[str] = None


class HarmonyAnalysis(BaseModel):
    """Knowledge base harmony analysis."""

    harmony_score: float = Field(ge=0.0, le=1.0)
    consonant_pairs: List[Tuple[str, str]]
    dissonant_pairs: List[Tuple[str, str]]
    suggested_reconciliations: List[str]


class SpectrumAnalyzer:
    """Analyzer for embedding spectral properties.

    Uses spectral analysis techniques to assess content quality,
    evidence reliability, and knowledge coherence.
    """

    def __init__(self, n_components: int = 64):
        """Initialize the spectrum analyzer.

        Args:
            n_components: Number of spectral components to analyze.
        """
        self.n_components = n_components
        self._analysis_count = 0
        self._total_embeddings_processed = 0
        logger.info(f"SpectrumAnalyzer initialized with {n_components} components")

    def compute_spectrum(self, embedding: np.ndarray) -> np.ndarray:
        """Compute the frequency spectrum of an embedding.

        Args:
            embedding: Input embedding vector.

        Returns:
            Frequency spectrum array (normalized magnitude).
        """
        # Ensure embedding is 1D
        embedding = np.asarray(embedding).flatten()

        # Pad or truncate to n_components for consistent FFT size
        if len(embedding) < self.n_components:
            padded = np.zeros(self.n_components)
            padded[: len(embedding)] = embedding
            embedding = padded
        elif len(embedding) > self.n_components:
            embedding = embedding[: self.n_components]

        # Compute FFT and get magnitude spectrum
        fft_result = np.fft.fft(embedding)
        spectrum = np.abs(fft_result)[: self.n_components // 2]

        # Normalize spectrum
        max_val = np.max(spectrum)
        if max_val > 0:
            spectrum = spectrum / max_val

        return spectrum

    def analyze_coherence(
        self,
        embeddings: List[np.ndarray],
        labels: Optional[List[str]] = None,
    ) -> CoherenceScore:
        """Analyze coherence of a set of embeddings.

        Args:
            embeddings: List of embedding vectors.
            labels: Optional labels for embeddings.

        Returns:
            CoherenceScore with detailed metrics.
        """
        if not embeddings:
            return CoherenceScore(
                overall_coherence=0.0,
                spectral_entropy=0.0,
                dominant_frequency=0.0,
                harmonic_ratio=0.0,
                discord_regions=[],
            )

        self._analysis_count += 1
        self._total_embeddings_processed += len(embeddings)

        # Compute spectra for all embeddings
        spectra = np.array([self.compute_spectrum(emb) for emb in embeddings])

        # Mean spectrum across all embeddings
        mean_spectrum = np.mean(spectra, axis=0)

        # Compute spectral entropy (measure of uniformity)
        # Higher entropy = less coherent (more uniform/random distribution)
        mean_spectrum_normalized = mean_spectrum / (np.sum(mean_spectrum) + 1e-10)
        spectral_entropy = -np.sum(
            mean_spectrum_normalized * np.log(mean_spectrum_normalized + 1e-10)
        )

        # Normalize entropy to [0, 1] range
        max_entropy = np.log(len(mean_spectrum))
        normalized_entropy = spectral_entropy / (max_entropy + 1e-10)

        # Find dominant frequency (index of max amplitude)
        dominant_idx = np.argmax(mean_spectrum)
        dominant_frequency = float(dominant_idx) / len(mean_spectrum)

        # Compute harmonic ratio (ratio of power in harmonics vs noise)
        # Harmonics are at multiples of dominant frequency
        harmonic_indices = []
        for k in range(1, 5):
            harm_idx = dominant_idx * k
            if harm_idx < len(mean_spectrum):
                harmonic_indices.append(harm_idx)

        if harmonic_indices:
            harmonic_power = np.sum(mean_spectrum[harmonic_indices])
            total_power = np.sum(mean_spectrum) + 1e-10
            harmonic_ratio = harmonic_power / total_power
        else:
            harmonic_ratio = 0.0

        # Identify discord regions (embeddings that deviate significantly)
        discord_regions = []
        if len(spectra) > 1:
            # Compute variance at each frequency bin across embeddings
            spectrum_var = np.var(spectra, axis=0)

            # Find regions of high variance
            threshold = np.mean(spectrum_var) + 2 * np.std(spectrum_var)
            high_var_indices = np.where(spectrum_var > threshold)[0]

            # Group consecutive indices into regions
            if len(high_var_indices) > 0:
                regions = []
                start = high_var_indices[0]
                end = high_var_indices[0]
                for idx in high_var_indices[1:]:
                    if idx == end + 1:
                        end = idx
                    else:
                        regions.append((int(start), int(end)))
                        start = idx
                        end = idx
                regions.append((int(start), int(end)))
                discord_regions = regions

        # Overall coherence: inverse of normalized entropy, boosted by harmonic ratio
        overall_coherence = (1.0 - normalized_entropy) * (0.5 + 0.5 * harmonic_ratio)
        overall_coherence = float(np.clip(overall_coherence, 0.0, 1.0))

        return CoherenceScore(
            overall_coherence=overall_coherence,
            spectral_entropy=float(spectral_entropy),
            dominant_frequency=float(dominant_frequency),
            harmonic_ratio=float(harmonic_ratio),
            discord_regions=discord_regions,
        )

    def weight_evidence_reliability(
        self,
        evidence_embeddings: List[Tuple[str, np.ndarray]],
        reference_spectrum: Optional[np.ndarray] = None,
    ) -> List[EvidenceReliability]:
        """Weight evidence by spectral reliability.

        Args:
            evidence_embeddings: List of (id, embedding) tuples.
            reference_spectrum: Optional reference spectrum for comparison.

        Returns:
            List of EvidenceReliability scores.
        """
        if not evidence_embeddings:
            return []

        self._analysis_count += 1
        self._total_embeddings_processed += len(evidence_embeddings)

        # Compute spectra for all evidence
        ids = [eid for eid, _ in evidence_embeddings]
        spectra = np.array([self.compute_spectrum(emb) for _, emb in evidence_embeddings])

        # Use mean spectrum as reference if not provided
        if reference_spectrum is None:
            reference_spectrum = np.mean(spectra, axis=0)
        else:
            reference_spectrum = self.compute_spectrum(reference_spectrum)

        results = []
        for i, (eid, _) in enumerate(evidence_embeddings):
            spectrum = spectra[i]

            # Compute spectral consistency (correlation with reference)
            if np.std(spectrum) > 0 and np.std(reference_spectrum) > 0:
                correlation = np.corrcoef(spectrum, reference_spectrum)[0, 1]
                spectral_consistency = float((correlation + 1) / 2)  # Map [-1,1] to [0,1]
            else:
                spectral_consistency = 0.5

            # Compute outlier degree (distance from mean spectrum)
            mse = np.mean((spectrum - reference_spectrum) ** 2)
            outlier_degree = float(np.sqrt(mse))

            # Reliability score: high consistency + low outlier degree
            reliability_score = spectral_consistency * np.exp(-outlier_degree)
            reliability_score = float(np.clip(reliability_score, 0.0, 1.0))

            results.append(
                EvidenceReliability(
                    evidence_id=eid,
                    reliability_score=reliability_score,
                    spectral_consistency=spectral_consistency,
                    outlier_degree=outlier_degree,
                )
            )

        return results

    def compute_attention_distribution(
        self,
        query_embedding: np.ndarray,
        source_embeddings: Dict[str, np.ndarray],
        temperature: float = 1.0,
    ) -> AttentionDistribution:
        """Compute spectral attention distribution.

        Args:
            query_embedding: Query vector.
            source_embeddings: Dict of source_id -> embedding.
            temperature: Softmax temperature (lower = sharper distribution).

        Returns:
            AttentionDistribution across sources.
        """
        if not source_embeddings:
            return AttentionDistribution(
                distribution={},
                entropy=0.0,
                concentration=1.0,
                dominant_source=None,
            )

        self._analysis_count += 1
        self._total_embeddings_processed += len(source_embeddings) + 1

        # Compute query spectrum
        query_spectrum = self.compute_spectrum(query_embedding)

        # Compute spectral similarities
        similarities = {}
        for source_id, source_emb in source_embeddings.items():
            source_spectrum = self.compute_spectrum(source_emb)

            # Use spectral correlation as similarity
            if np.std(query_spectrum) > 0 and np.std(source_spectrum) > 0:
                corr = np.corrcoef(query_spectrum, source_spectrum)[0, 1]
                # Handle NaN from correlation
                if np.isnan(corr):
                    corr = 0.0
                similarities[source_id] = float(corr)
            else:
                similarities[source_id] = 0.0

        # Apply softmax to get distribution
        source_ids = list(similarities.keys())
        scores = np.array([similarities[sid] for sid in source_ids])

        # Temperature-scaled softmax
        scores_scaled = scores / (temperature + 1e-10)
        scores_exp = np.exp(scores_scaled - np.max(scores_scaled))  # Numerically stable
        probs = scores_exp / (np.sum(scores_exp) + 1e-10)

        distribution = {sid: float(probs[i]) for i, sid in enumerate(source_ids)}

        # Compute entropy of distribution
        entropy = -np.sum(probs * np.log(probs + 1e-10))

        # Concentration is inverse of normalized entropy
        max_entropy = np.log(len(probs)) if len(probs) > 1 else 1.0
        normalized_entropy = entropy / (max_entropy + 1e-10)
        concentration = 1.0 - normalized_entropy

        # Find dominant source
        dominant_idx = np.argmax(probs)
        dominant_source = source_ids[dominant_idx] if source_ids else None

        return AttentionDistribution(
            distribution=distribution,
            entropy=float(entropy),
            concentration=float(concentration),
            dominant_source=dominant_source,
        )

    def analyze_harmony(
        self,
        concept_embeddings: Dict[str, np.ndarray],
        threshold: float = 0.5,
    ) -> HarmonyAnalysis:
        """Analyze harmony/discord in knowledge base.

        Args:
            concept_embeddings: Dict of concept -> embedding.
            threshold: Threshold for consonance/dissonance classification.

        Returns:
            HarmonyAnalysis with consonant/dissonant pairs.
        """
        if len(concept_embeddings) < 2:
            return HarmonyAnalysis(
                harmony_score=1.0,
                consonant_pairs=[],
                dissonant_pairs=[],
                suggested_reconciliations=[],
            )

        self._analysis_count += 1
        self._total_embeddings_processed += len(concept_embeddings)

        # Compute spectra for all concepts
        concepts = list(concept_embeddings.keys())
        spectra = {c: self.compute_spectrum(concept_embeddings[c]) for c in concepts}

        # Compute pairwise spectral correlations
        consonant_pairs = []
        dissonant_pairs = []
        correlations = []

        for i in range(len(concepts)):
            for j in range(i + 1, len(concepts)):
                c1, c2 = concepts[i], concepts[j]
                s1, s2 = spectra[c1], spectra[c2]

                # Compute correlation
                if np.std(s1) > 0 and np.std(s2) > 0:
                    corr = np.corrcoef(s1, s2)[0, 1]
                    if np.isnan(corr):
                        corr = 0.0
                else:
                    corr = 0.0

                correlations.append(corr)

                # Classify as consonant or dissonant
                # Consonant: high positive correlation (harmonious)
                # Dissonant: negative or low correlation (conflicting)
                if corr >= threshold:
                    consonant_pairs.append((c1, c2))
                elif corr < -threshold:
                    dissonant_pairs.append((c1, c2))

        # Overall harmony score: fraction of consonant pairs
        total_pairs = len(correlations)
        if total_pairs > 0:
            harmony_score = len(consonant_pairs) / total_pairs
            # Penalize for dissonant pairs
            harmony_score *= 1.0 - (len(dissonant_pairs) / total_pairs) * 0.5
            harmony_score = float(np.clip(harmony_score, 0.0, 1.0))
        else:
            harmony_score = 1.0

        # Generate reconciliation suggestions for dissonant pairs
        suggested_reconciliations = []
        for c1, c2 in dissonant_pairs[:5]:  # Limit to top 5
            suggested_reconciliations.append(
                f"Reconcile concepts '{c1}' and '{c2}': "
                f"Consider clarifying semantic boundaries or adding bridging evidence."
            )

        return HarmonyAnalysis(
            harmony_score=harmony_score,
            consonant_pairs=consonant_pairs,
            dissonant_pairs=dissonant_pairs,
            suggested_reconciliations=suggested_reconciliations,
        )

    def detect_anomalies(
        self,
        embeddings: List[np.ndarray],
        sensitivity: float = 2.0,
    ) -> List[int]:
        """Detect spectral anomalies in embeddings.

        Args:
            embeddings: List of embeddings to analyze.
            sensitivity: Standard deviations for anomaly detection.

        Returns:
            Indices of anomalous embeddings.
        """
        if len(embeddings) < 2:
            return []

        self._analysis_count += 1
        self._total_embeddings_processed += len(embeddings)

        # Compute spectra for all embeddings
        spectra = np.array([self.compute_spectrum(emb) for emb in embeddings])

        # Compute mean spectrum and standard deviation
        mean_spectrum = np.mean(spectra, axis=0)
        std_spectrum = np.std(spectra, axis=0) + 1e-10

        # Compute z-scores for each embedding's spectrum
        anomalies = []
        for i, spectrum in enumerate(spectra):
            z_scores = np.abs(spectrum - mean_spectrum) / std_spectrum
            max_z = np.max(z_scores)

            # Flag as anomaly if max z-score exceeds sensitivity threshold
            if max_z > sensitivity:
                anomalies.append(i)

        return anomalies

    def compute_spectral_distance(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray,
    ) -> float:
        """Compute spectral distance between two embeddings.

        Args:
            embedding1: First embedding vector.
            embedding2: Second embedding vector.

        Returns:
            Spectral distance (0 = identical spectra, higher = more different).
        """
        spectrum1 = self.compute_spectrum(embedding1)
        spectrum2 = self.compute_spectrum(embedding2)

        # Use L2 distance in spectral domain
        distance = np.sqrt(np.sum((spectrum1 - spectrum2) ** 2))

        return float(distance)

    def get_stats(self) -> Dict[str, Any]:
        """Get analyzer statistics."""
        return {
            "n_components": self.n_components,
            "analysis_count": self._analysis_count,
            "total_embeddings_processed": self._total_embeddings_processed,
        }


# Global singleton
spectrum_analyzer = SpectrumAnalyzer()


__all__ = [
    "SpectrumAnalyzer",
    "CoherenceScore",
    "EvidenceReliability",
    "AttentionDistribution",
    "HarmonyAnalysis",
    "spectrum_analyzer",
]
