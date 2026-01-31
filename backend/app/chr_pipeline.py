from __future__ import annotations
import os
from dataclasses import dataclass
from typing import List, Dict, Tuple

import numpy as np


def _maybe_st_model():
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    except Exception:
        return None


def embed_texts(texts: List[str]) -> Tuple[np.ndarray, str]:
    texts = [t if isinstance(t, str) else str(t) for t in texts]
    model = _maybe_st_model()
    if model is not None:
        try:
            vecs = model.encode(
                texts, batch_size=32, show_progress_bar=False, convert_to_numpy=True, normalize_embeddings=True
            )
            return vecs.astype(np.float32), "sentence-transformers/all-MiniLM-L6-v2"
        except Exception:
            pass
    # Fallback: hashing vectorizer
    from sklearn.feature_extraction.text import HashingVectorizer  # type: ignore

    hv = HashingVectorizer(n_features=2**12, alternate_sign=False, norm=None)
    X = hv.transform(texts).astype(np.float32)
    X = X.toarray()
    # l2-normalize
    norms = np.linalg.norm(X, axis=1, keepdims=True) + 1e-9
    X = X / norms
    return X.astype(np.float32), "HashingVectorizer"


def _init_anchors(Z: np.ndarray, K: int, seed: int = 42) -> np.ndarray:
    # PCA/SVD-based init for stability
    rng = np.random.default_rng(seed)
    # pick K random rows and orthonormalize
    idx = rng.choice(Z.shape[0], size=min(K, Z.shape[0]), replace=False)
    U = Z[idx]
    # l2 normalize rows
    U = U / (np.linalg.norm(U, axis=1, keepdims=True) + 1e-9)
    if U.shape[0] < K:
        # pad with random
        pad = rng.normal(size=(K - U.shape[0], Z.shape[1]))
        pad = pad / (np.linalg.norm(pad, axis=1, keepdims=True) + 1e-9)
        U = np.vstack([U, pad])
    return U.astype(np.float32)


def _softmax(x: np.ndarray, axis: int = 1) -> np.ndarray:
    x = x - x.max(axis=axis, keepdims=True)
    e = np.exp(x)
    return e / (e.sum(axis=axis, keepdims=True) + 1e-9)


def _entropy(arr: np.ndarray, bins: int = 16) -> float:
    # Handle edge case: if all values are identical, entropy is 0
    data_range = arr.max() - arr.min()
    if data_range == 0:
        return 0.0
    # Limit bins to the number of unique values to avoid numpy error
    unique_vals = len(np.unique(arr))
    bins = min(bins, unique_vals) if unique_vals > 0 else 1
    try:
        hist, _ = np.histogram(arr, bins=bins, density=True)
    except ValueError:
        # If histogram fails (e.g., edge case with few unique values),
        # fall back to simpler entropy calculation or return 0
        try:
            hist, _ = np.histogram(arr, bins="auto", density=True)
        except ValueError:
            # Data has too little variation for any binning - return 0 entropy
            return 0.0
    p = hist / (hist.sum() + 1e-9)
    p = p[p > 0]
    return float(-(p * np.log(p)).sum())


@dataclass
class CHRResult:
    backend: str
    K: int
    mhep: float
    Hg: float
    Hs: float
    Hg_traj: List[float]
    Hs_traj: List[float]
    labels: List[int]
    order: List[int]
    rows: List[Dict]
    Z: np.ndarray
    U: np.ndarray


def run_chr(units: List[str], K: int = 8, iters: int = 30, bins: int = 8, beta: float = 12.0, seed: int = 42) -> CHRResult:
    if not units:
        raise ValueError("No units provided")
    Z, backend = embed_texts(units)

    # Initialize anchors
    U = _init_anchors(Z, K=K, seed=seed)

    Hg_traj: List[float] = []
    Hs_traj: List[float] = []

    for _ in range(iters):
        U_norm = U / (np.linalg.norm(U, axis=1, keepdims=True) + 1e-9)
        proj = Z @ U_norm.T  # [N, K]
        # Soft assignments over constellations
        p = _softmax(beta * proj, axis=1)  # [N, K]
        # Update anchors as weighted means
        U_new = np.zeros_like(U)
        for j in range(K):
            w = p[:, j:j+1]
            num = (w * Z).sum(axis=0)
            if np.linalg.norm(num) < 1e-8:
                U_new[j] = U[j]
            else:
                U_new[j] = num / (np.linalg.norm(num) + 1e-9)
        U = U_new

        # Entropy measures
        r = proj.max(axis=1)
        Hg = _entropy(r, bins=bins)
        Hs_list = []
        for j in range(K):
            Hs_list.append(_entropy(proj[:, j], bins=bins))
        Hs = float(np.mean(Hs_list)) if Hs_list else Hg
        Hg_traj.append(float(Hg))
        Hs_traj.append(float(Hs))

    # Final projections and hard labels
    U_norm = U / (np.linalg.norm(U, axis=1, keepdims=True) + 1e-9)
    proj = Z @ U_norm.T
    labels = proj.argmax(axis=1)
    r = proj.max(axis=1)

    # Simple MHEP based on relative drop from the first to last iteration
    if len(Hg_traj) >= 2 and Hg_traj[0] > 1e-9 and Hs_traj[0] > 1e-9:
        drop_g = max(0.0, (Hg_traj[0] - Hg_traj[-1]) / Hg_traj[0])
        drop_s = max(0.0, (Hs_traj[0] - Hs_traj[-1]) / Hs_traj[0])
        mhep = (drop_g + drop_s) * 50.0
    else:
        mhep = 0.0

    order_idx = np.argsort(-r)
    rows: List[Dict] = []
    for idx in order_idx:
        rows.append({
            "idx": int(idx),
            "constellation": int(labels[idx]),
            "radius": float(r[idx]),
            "text": units[idx],
        })

    return CHRResult(
        backend=backend,
        K=K,
        mhep=float(mhep),
        Hg=float(Hg_traj[-1] if Hg_traj else 0.0),
        Hs=float(Hs_traj[-1] if Hs_traj else 0.0),
        Hg_traj=[float(x) for x in Hg_traj],
        Hs_traj=[float(x) for x in Hs_traj],
        labels=[int(x) for x in labels],
        order=[int(x) for x in order_idx],
        rows=rows,
        Z=Z,
        U=U_norm,
    )


def pca_plot(Z: np.ndarray, U_norm: np.ndarray, labels: np.ndarray, out_path: str) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from sklearn.decomposition import PCA  # type: ignore

        pca = PCA(n_components=2, random_state=0)
        Z2 = pca.fit_transform(Z)
        U2 = pca.transform(U_norm)

        plt.figure(figsize=(6, 5))
        plt.scatter(Z2[:, 0], Z2[:, 1], s=10, c=labels, cmap="tab20", alpha=0.8)
        plt.scatter(U2[:, 0], U2[:, 1], marker="*", s=160, c="black")
        plt.title("CHR PCA Map")
        plt.tight_layout()
        plt.savefig(out_path, dpi=120)
        plt.close()
    except Exception:
        # plotting failure should not crash pipeline
        pass
