"""Advanced table utilities for Docling PDF output."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

import pandas as pd


class AdvancedTableProcessor:
    """Post-process Docling tables to detect multi-page spans."""

    def __init__(self) -> None:
        # For now, continuity is determined by contiguous pages and identical headers.
        self._previous_entry: Optional[Dict[str, Any]] = None

    def detect_spanning_tables(self, doc: Any) -> List[Dict[str, Any]]:
        """Group Docling tables and merge multi-page spans.

        Parameters
        ----------
        doc:
            Docling document returned by :class:`DocumentConverter`.

        Returns
        -------
        list of dict
            Each dictionary contains the merged dataframe plus metadata describing
            the pages and bounding boxes that contributed to the final table.
        """

        tables: List[Dict[str, Any]] = []
        self._previous_entry = None

        pages: Iterable[Any] = getattr(doc, "pages", []) or []
        # Fallback to doc.tables when Docling skips page objects (rare but possible)
        if not pages and getattr(doc, "tables", None):
            pages = [type("Page", (), {"tables": getattr(doc, "tables", [])})()]

        for page_idx, page in enumerate(pages):
            for table in getattr(page, "tables", []) or []:
                df = self._table_to_dataframe(table)
                if df is None:
                    # Reset continuity – we cannot compare headers without data.
                    self._previous_entry = None
                    continue

                segment = self._extract_segment(table, page_idx)
                entry = {
                    "dataframe": df,
                    "pages": [page_idx],
                    "segments": [segment],
                    "merged": False,
                    "header_detected": self._detect_header(df),
                }

                if self._previous_entry and self._is_continuation(self._previous_entry, df, page_idx):
                    self._previous_entry["dataframe"] = pd.concat(
                        [self._previous_entry["dataframe"], df], ignore_index=True
                    )
                    self._previous_entry["pages"].append(page_idx)
                    self._previous_entry["segments"].append(segment)
                    self._previous_entry["merged"] = True
                else:
                    tables.append(entry)
                    self._previous_entry = entry

        return tables

    def _table_to_dataframe(self, table: Any) -> Optional[pd.DataFrame]:
        try:
            df = table.export_to_dataframe()
            if isinstance(df, pd.DataFrame):
                return df
        except Exception:
            return None
        return None

    def _extract_segment(self, table: Any, page_idx: int) -> Dict[str, Any]:
        bbox_tuple: Optional[tuple[float, float, float, float]] = None
        try:
            prov = getattr(table, "prov", None)
            if prov:
                bbox = getattr(prov[0], "bbox", None)
                if bbox and hasattr(bbox, "as_tuple"):
                    bbox_tuple = tuple(bbox.as_tuple())  # type: ignore[arg-type]
        except Exception:
            bbox_tuple = None
        return {"page": page_idx, "bbox": bbox_tuple}

    def _columns_signature(self, df: pd.DataFrame) -> List[str]:
        return [str(col).strip().lower() for col in df.columns]

    def _is_continuation(self, previous: Dict[str, Any], current_df: pd.DataFrame, current_page: int) -> bool:
        prev_pages: List[int] = previous.get("pages", [])
        if not prev_pages:
            return False
        prev_page = prev_pages[-1]
        if current_page <= prev_page:
            return False
        # Only join immediately subsequent pages; anything else is treated as a new table.
        if current_page - prev_page > 1:
            return False

        prev_df: pd.DataFrame = previous.get("dataframe")
        if prev_df is None or not isinstance(prev_df, pd.DataFrame):
            return False

        return self._columns_signature(prev_df) == self._columns_signature(current_df)

    def _detect_header(self, df: pd.DataFrame) -> bool:
        if df.empty:
            return False
        first_row = df.iloc[0]
        # Treat the first row as a header if most values are strings or non-numeric tokens.
        string_like = 0
        for value in first_row.tolist():
            if isinstance(value, str) and value.strip():
                string_like += 1
            else:
                try:
                    float(value)
                except Exception:
                    string_like += 1
        return string_like >= max(1, len(first_row) // 2)
