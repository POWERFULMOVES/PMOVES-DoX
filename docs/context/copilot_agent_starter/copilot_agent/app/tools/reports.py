import pandas as pd
from io import StringIO
from typing import Optional

def summarize_table(csv_text: str, groupby: Optional[str] = None) -> str:
    df = pd.read_csv(StringIO(csv_text))
    lines = [f"Rows: {len(df)}, Cols: {list(df.columns)}"]
    nums = df.select_dtypes("number").describe().to_dict()
    lines.append("Numeric summary (describe):")
    for col, stats in nums.items():
        stats_str = ", ".join(f"{k}={v:.2f}" for k, v in stats.items())
        lines.append(f" - {col}: {stats_str}")
    if groupby and groupby in df.columns:
        gb = df.groupby(groupby).sum(numeric_only=True).reset_index()
        lines.append(f"Grouped by {groupby}:")
        for _, row in gb.iterrows():
            lines.append(" - " + ", ".join(f"{c}={row[c]}" for c in gb.columns))
    return "\n".join(lines)
