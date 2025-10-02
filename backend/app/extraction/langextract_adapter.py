from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import langextract as lx  # type: ignore


def build_examples(raw_examples: Optional[List[Dict[str, Any]]]) -> List[lx.data.ExampleData]:
    examples: List[lx.data.ExampleData] = []
    if not raw_examples:
        return examples
    for ex in raw_examples:
        extractions = []
        for item in ex.get("extractions", []) or []:
            extractions.append(
                lx.data.Extraction(
                    extraction_class=item.get("extraction_class", "entity"),
                    extraction_text=item.get("extraction_text", ""),
                    attributes=item.get("attributes", {}) or {},
                )
            )
        examples.append(
            lx.data.ExampleData(
                text=ex.get("text", ""),
                extractions=extractions,
            )
        )
    return examples


def run_langextract(
    text: str,
    prompt_description: str,
    examples: Optional[List[Dict[str, Any]]] = None,
    model_id: Optional[str] = None,
    api_key: Optional[str] = None,
    max_workers: int = 8,
    extraction_passes: int = 1,
    max_char_buffer: int = 4000,
) -> Dict[str, Any]:
    """Run LangExtract over a text blob and return the structured result dict.

    The caller is responsible for persisting JSONL/HTML artifacts if desired.
    """
    if api_key:
        os.environ["LANGEXTRACT_API_KEY"] = api_key

    model = model_id or os.getenv("LANGEXTRACT_MODEL", "gemini-2.5-flash")

    # Provider-specific params (Ollama / local)
    language_model_params: Dict[str, Any] = {}
    if model.startswith("ollama:") or os.getenv("LANGEXTRACT_PROVIDER") == "ollama":
        # Allow model id like 'ollama:gemma3'
        if model.startswith("ollama:"):
            model = model.split(":", 1)[1]
        language_model_params = {
            "ollama": True,
            "base_url": os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
        }

    result = lx.extract(
        text_or_documents=text,
        prompt_description=prompt_description,
        examples=build_examples(examples),
        model_id=model,
        language_model_params=language_model_params or None,
        extraction_passes=extraction_passes,
        max_workers=max_workers,
        max_char_buffer=max_char_buffer,
    )

    # Convert to plain dict the library’s object
    out = {
        "model_id": model,
        "document_count": 1,
        "entities": [e.model_dump() for e in result.extractions],
        "metadata": getattr(result, "metadata", {}),
    }
    return out


def write_visualization(
    result: Dict[str, Any],
    output_dir: Path,
    output_name: str = "langextract_results",
) -> Path:
    """Save JSONL and HTML visualization to output_dir; return HTML path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / f"{output_name}.jsonl"
    # langextract expects a list of annotated documents; we reconstruct a minimal one
    doc = lx.data.AnnotatedDocument(
        text="",
        extractions=[lx.data.Extraction(**e) for e in result.get("entities", [])],
    )
    lx.io.save_annotated_documents([doc], output_name=jsonl_path.stem, output_dir=str(output_dir))
    html = lx.visualize(str(jsonl_path))
    html_path = output_dir / f"{output_name}.html"
    with open(html_path, "w", encoding="utf-8") as f:
        if hasattr(html, "data"):
            f.write(html.data)
        else:
            f.write(str(html))
    return html_path
