from __future__ import annotations

from typing import Any, Dict, Iterable, List, Sequence, Tuple

import pandas as pd


class ComplexTableProcessor:
    """Normalize Docling tables with merged cells and multi-level headers."""

    def normalize_table(self, table_data: Any) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Return a normalized dataframe and header metadata for a table."""
        merged_df = self.process_merged_cells(table_data)
        header_info = self.detect_multi_level_headers(merged_df)
        normalized_df = self._apply_headers(merged_df, header_info)
        return normalized_df, header_info

    def process_merged_cells(self, table_data: Any) -> pd.DataFrame:
        """Expand merged cells using Docling span metadata when available."""
        if isinstance(table_data, pd.DataFrame):
            return table_data.copy()

        cells: Iterable[Any] | None = None
        if hasattr(table_data, "cells"):
            cells = getattr(table_data, "cells")
        elif isinstance(table_data, dict) and "cells" in table_data:
            cells = table_data["cells"]

        if cells is None:
            if hasattr(table_data, "export_to_dataframe"):
                return table_data.export_to_dataframe()
            return pd.DataFrame()

        cell_list = list(cells)
        if not cell_list:
            if hasattr(table_data, "export_to_dataframe"):
                return table_data.export_to_dataframe()
            return pd.DataFrame()

        max_row = 0
        max_col = 0
        parsed_cells: List[Tuple[int, int, int, int, str]] = []
        for cell in cell_list:
            row_idx = int(self._extract_attr(cell, ["row_index", "row", "r"], default=0))
            col_idx = int(self._extract_attr(cell, ["column_index", "col", "c"], default=0))
            row_span = int(self._extract_attr(cell, ["row_span", "rowspan", "rs"], default=1) or 1)
            col_span = int(self._extract_attr(cell, ["col_span", "colspan", "cs"], default=1) or 1)
            text = self._stringify(self._extract_attr(cell, ["text", "value", "content"], default=""))
            max_row = max(max_row, row_idx + row_span)
            max_col = max(max_col, col_idx + col_span)
            parsed_cells.append((row_idx, col_idx, row_span, col_span, text))

        grid: List[List[str | None]] = [[None for _ in range(max_col)] for _ in range(max_row)]

        for row_idx, col_idx, row_span, col_span, text in parsed_cells:
            for r in range(row_span):
                for c in range(col_span):
                    target_r = row_idx + r
                    target_c = col_idx + c
                    if target_r >= len(grid) or target_c >= len(grid[target_r]):
                        continue
                    if r == 0 and c == 0:
                        grid[target_r][target_c] = text
                    elif not grid[target_r][target_c]:
                        grid[target_r][target_c] = text

        dataframe = pd.DataFrame(grid)
        return dataframe

    def detect_multi_level_headers(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect header rows (up to three levels) at the top of the table."""
        if df.empty:
            return {"levels": 0, "headers": []}

        header_rows: List[List[str]] = []
        max_rows = min(3, len(df))
        for idx in range(max_rows):
            row = df.iloc[idx]
            if self._is_header_row(row):
                header_rows.append([self._stringify(v) for v in row.tolist()])
            else:
                break

        return {
            "levels": len(header_rows),
            "headers": header_rows,
        }

    def _apply_headers(self, df: pd.DataFrame, header_info: Dict[str, Any]) -> pd.DataFrame:
        """Apply detected headers to produce a normalized dataframe."""
        normalized = df.copy()
        levels = int(header_info.get("levels") or 0)
        header_rows = header_info.get("headers") or []

        if levels > 0 and header_rows:
            width = normalized.shape[1]
            tuples: List[Tuple[str, ...]] = []
            for col_idx in range(width):
                labels: List[str] = []
                for level_idx in range(levels):
                    row_values = header_rows[level_idx] if level_idx < len(header_rows) else []
                    label = ""
                    if col_idx < len(row_values):
                        label = self._stringify(row_values[col_idx])
                    labels.append(label)
                tuples.append(tuple(labels))

            try:
                normalized.columns = pd.MultiIndex.from_tuples(tuples)
            except Exception:
                flattened = [self._combine_labels(labels, idx) for idx, labels in enumerate(tuples)]
                normalized.columns = flattened
            else:
                normalized = normalized.iloc[levels:].reset_index(drop=True)
                normalized.columns = self._flatten_multiindex(normalized.columns)
                return normalized

            normalized = normalized.iloc[levels:].reset_index(drop=True)
            normalized.columns = self._ensure_string_columns(normalized.columns)
            return normalized

        # Fallback: treat first row as header when it contains strings
        if len(normalized) > 0:
            first_row = normalized.iloc[0].tolist()
            header_candidate = [self._stringify(v) for v in first_row]
            if any(header_candidate):
                normalized = normalized.iloc[1:].reset_index(drop=True)
                normalized.columns = [label or f"column_{idx}" for idx, label in enumerate(header_candidate)]
                return normalized

        normalized.columns = self._ensure_string_columns(normalized.columns)
        return normalized

    def _is_header_row(self, row: pd.Series) -> bool:
        values = [self._stringify(v) for v in row.tolist() if not self._is_empty(v)]
        if not values:
            return False
        alpha_tokens = sum(1 for v in values if any(ch.isalpha() for ch in v))
        if alpha_tokens == 0:
            return False
        numeric_tokens = sum(1 for v in values if self._looks_numeric(v))
        total = len(values)
        if total == 0:
            return False
        return (
            alpha_tokens >= max(1, total - numeric_tokens)
            and (alpha_tokens / total) >= 0.5
        )

    def _looks_numeric(self, value: str) -> bool:
        stripped = value.replace(",", "").replace("$", "").replace("%", "").strip()
        if not stripped:
            return False
        if stripped.startswith("(") and stripped.endswith(")"):
            stripped = stripped[1:-1]
        try:
            float(stripped)
            return True
        except ValueError:
            return False

    def _is_empty(self, value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, float) and pd.isna(value):
            return True
        return self._stringify(value) == ""

    def _extract_attr(self, cell: Any, names: Sequence[str], default: Any) -> Any:
        for name in names:
            if isinstance(cell, dict) and name in cell:
                return cell[name]
            if hasattr(cell, name):
                return getattr(cell, name)
        return default

    def _stringify(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, float) and pd.isna(value):
            return ""
        return str(value).strip()

    def _combine_labels(self, labels: Sequence[str], idx: int) -> str:
        cleaned = self._deduplicate_labels(label for label in labels if label)
        if cleaned:
            return " / ".join(cleaned)
        return f"column_{idx}"

    def _flatten_multiindex(self, columns: pd.MultiIndex) -> List[str]:
        flattened: List[str] = []
        for idx, col in enumerate(columns.tolist()):
            if isinstance(col, tuple):
                cleaned = self._deduplicate_labels(
                    self._stringify(part) for part in col if self._stringify(part)
                )
                flattened.append(" / ".join(cleaned) if cleaned else f"column_{idx}")
            else:
                flattened.append(self._stringify(col) or f"column_{idx}")
        return flattened

    def _ensure_string_columns(self, columns: Iterable[Any]) -> List[str]:
        ensured: List[str] = []
        for idx, col in enumerate(columns):
            label = self._stringify(col)
            ensured.append(label or f"column_{idx}")
        return ensured

    def _deduplicate_labels(self, labels: Iterable[str]) -> List[str]:
        seen: List[str] = []
        for label in labels:
            if label and label not in seen:
                seen.append(label)
        return seen
