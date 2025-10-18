from __future__ import annotations

from typing import Any, Dict, Iterable, List, Sequence, Tuple

import pandas as pd


class FinancialStatementDetector:
    """Detect and summarize financial statements extracted from tables."""

    STATEMENT_TYPES: Dict[str, Sequence[str]] = {
        "balance_sheet": ("assets", "liabilities", "equity"),
        "income_statement": ("revenue", "expenses", "net income"),
        "cash_flow": ("operating", "investing", "financing"),
    }

    def analyze_table(
        self, table_df: pd.DataFrame, header_info: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """Return classification and summary for a financial table."""
        stmt_type, confidence = self.detect_statement_type(table_df, header_info)
        summary = self.parse_financial_statement(table_df, stmt_type)
        return {
            "type": stmt_type,
            "confidence": round(confidence, 4),
            "summary": summary,
        }

    def detect_statement_type(
        self, table_df: pd.DataFrame, header_info: Dict[str, Any] | None = None
    ) -> Tuple[str, float]:
        """Classify table into a financial statement type."""
        text_parts: List[str] = []
        columns = self._stringify_columns(table_df.columns)
        text_parts.extend(columns)

        if header_info and header_info.get("headers"):
            for header_row in header_info["headers"]:
                text_parts.extend(str(cell).lower() for cell in header_row if cell)

        flattened = table_df.fillna("").astype(str).values.flatten().tolist()
        text_parts.extend(val.lower() for val in flattened if val)

        combined = " ".join(text_parts)
        best_type = "unknown"
        best_score = 0.0
        for stmt_type, keywords in self.STATEMENT_TYPES.items():
            matches = sum(1 for kw in keywords if kw in combined)
            score = matches / len(keywords)
            if matches >= 2 and score > best_score:
                best_type = stmt_type
                best_score = score
        return best_type, best_score

    def parse_financial_statement(self, table_df: pd.DataFrame, stmt_type: str) -> Dict[str, Any]:
        """Extract structured metrics for supported statement types."""
        if stmt_type == "income_statement":
            return self._parse_income_statement(table_df)
        if stmt_type == "balance_sheet":
            return self._parse_balance_sheet(table_df)
        if stmt_type == "cash_flow":
            return self._parse_cash_flow(table_df)
        return {}

    # ---- Income statement helpers -------------------------------------------------
    def _parse_income_statement(self, df: pd.DataFrame) -> Dict[str, Any]:
        return {
            "revenue": self._find_value(df, ("revenue", "total revenue")),
            "expenses": self._find_value(df, ("expenses", "total expenses")),
            "net_income": self._find_value(df, ("net income", "profit")),
            "gross_profit": self._find_value(df, ("gross profit",)),
        }

    # ---- Balance sheet helpers ----------------------------------------------------
    def _parse_balance_sheet(self, df: pd.DataFrame) -> Dict[str, Any]:
        assets = self._find_value(df, ("total assets", "assets"))
        liabilities = self._find_value(df, ("total liabilities", "liabilities"))
        equity = self._find_value(df, ("total equity", "equity"))
        return {
            "total_assets": assets,
            "total_liabilities": liabilities,
            "total_equity": equity,
            "liabilities_plus_equity": self._safe_sum(liabilities, equity),
        }

    # ---- Cash flow helpers --------------------------------------------------------
    def _parse_cash_flow(self, df: pd.DataFrame) -> Dict[str, Any]:
        operating = self._find_value(df, ("net cash provided by operating", "operating activities"))
        investing = self._find_value(df, ("net cash used in investing", "investing activities"))
        financing = self._find_value(df, ("net cash used in financing", "financing activities"))
        net_change = self._find_value(df, ("net increase", "net decrease", "net change"))
        return {
            "operating": operating,
            "investing": investing,
            "financing": financing,
            "net_change": net_change,
        }

    # ---- Shared utilities ---------------------------------------------------------
    def _find_value(self, df: pd.DataFrame, search_terms: Sequence[str]) -> float | None:
        if df.empty:
            return None
        columns = list(df.columns)
        label_col = columns[0] if columns else None
        for _, row in df.iterrows():
            label = self._extract_label(row, label_col)
            if not label:
                continue
            label_lower = label.lower()
            if any(term in label_lower for term in search_terms):
                values = row.tolist()
                if label_col is not None and values:
                    values = values[1:]
                for value in values:
                    numeric = self._to_numeric(value)
                    if numeric is not None:
                        return numeric
                for value in reversed(row.tolist()):
                    numeric = self._to_numeric(value)
                    if numeric is not None:
                        return numeric
        return None

    def _extract_label(self, row: pd.Series, label_col: Any | None) -> str:
        if label_col is not None and label_col in row:
            return str(row[label_col])
        for value in row.tolist():
            text = str(value)
            if not self._to_numeric(value) and any(ch.isalpha() for ch in text):
                return text
        return ""

    def _to_numeric(self, value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)) and not pd.isna(value):
            return float(value)
        stringified = str(value).strip()
        if not stringified:
            return None
        stringified = stringified.replace(",", "")
        stringified = stringified.replace("$", "")
        negative = False
        if stringified.startswith("(") and stringified.endswith(")"):
            negative = True
            stringified = stringified[1:-1]
        if stringified.endswith("%"):
            stringified = stringified[:-1]
        try:
            result = float(stringified)
            return -result if negative else result
        except ValueError:
            return None

    def _safe_sum(self, *values: float | None) -> float | None:
        numeric_values = [v for v in values if v is not None]
        if not numeric_values:
            return None
        return float(sum(numeric_values))

    def _stringify_columns(self, columns: Iterable[Any]) -> List[str]:
        out: List[str] = []
        for col in columns:
            if isinstance(col, tuple):
                cleaned = [str(part).lower() for part in col if str(part).strip()]
                out.append(" ".join(cleaned))
            else:
                out.append(str(col).lower())
        return out
