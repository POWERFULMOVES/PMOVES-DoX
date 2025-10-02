from pathlib import Path
import pandas as pd
import uuid
from typing import List, Dict, Tuple

def process_csv(file_path: Path, report_week: str) -> Tuple[List[Dict], List[Dict]]:
    """Process CSV file and extract facts"""
    df = pd.read_csv(file_path)
    
    facts = []
    evidence = []
    evidence_id = str(uuid.uuid4())
    
    # Calculate totals
    metrics = {}
    numeric_cols = df.select_dtypes(include=['number']).columns
    
    for col in numeric_cols:
        col_lower = col.lower()
        if any(x in col_lower for x in ['spend', 'cost']):
            metrics['spend'] = float(df[col].sum())
        elif 'revenue' in col_lower:
            metrics['revenue'] = float(df[col].sum())
        elif 'conversion' in col_lower:
            metrics['conversions'] = float(df[col].sum())
        elif 'click' in col_lower:
            metrics['clicks'] = float(df[col].sum())
        elif 'impression' in col_lower:
            metrics['impressions'] = float(df[col].sum())
    
    # Calculate derived metrics
    if 'clicks' in metrics and 'impressions' in metrics and metrics['impressions'] > 0:
        metrics['ctr'] = metrics['clicks'] / metrics['impressions']
    
    if 'spend' in metrics and 'conversions' in metrics and metrics['conversions'] > 0:
        metrics['cpa'] = metrics['spend'] / metrics['conversions']
    
    if 'revenue' in metrics and 'spend' in metrics and metrics['spend'] > 0:
        metrics['roas'] = metrics['revenue'] / metrics['spend']
    
    evidence.append({
        "id": evidence_id,
        "locator": f"{file_path.name}#data",
        "preview": df.head(10).to_string(),
        "content_type": "csv",
        "full_data": df.to_dict('records')
    })
    
    facts.append({
        "id": str(uuid.uuid4()),
        "report_week": report_week,
        "entity": None,
        "metrics": metrics,
        "evidence_id": evidence_id
    })
    
    return facts, evidence
