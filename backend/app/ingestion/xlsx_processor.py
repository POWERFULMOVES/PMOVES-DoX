from pathlib import Path
import pandas as pd
import uuid
from typing import List, Dict, Tuple

def process_xlsx(file_path: Path, report_week: str) -> Tuple[List[Dict], List[Dict]]:
    """Process Excel file and extract facts"""
    xls = pd.ExcelFile(file_path)
    
    facts = []
    evidence = []
    
    # Process each sheet
    for sheet_name in xls.sheet_names:
        df = xls.parse(sheet_name)
        evidence_id = str(uuid.uuid4())
        
        # Calculate totals
        metrics = {}
        numeric_cols = df.select_dtypes(include=['number']).columns
        
        for col in numeric_cols:
            col_lower = col.lower()
            if any(x in col_lower for x in ['spend', 'cost']):
                metrics['spend'] = metrics.get('spend', 0) + float(df[col].sum())
            elif 'revenue' in col_lower:
                metrics['revenue'] = metrics.get('revenue', 0) + float(df[col].sum())
            elif 'conversion' in col_lower or 'lead' in col_lower:
                metrics['conversions'] = metrics.get('conversions', 0) + float(df[col].sum())
        
        evidence.append({
            "id": evidence_id,
            "locator": f"{file_path.name}#{sheet_name}",
            "preview": df.head(10).to_string(),
            "content_type": "xlsx",
            "full_data": df.to_dict('records')
        })
        
        if metrics:
            facts.append({
                "id": str(uuid.uuid4()),
                "report_week": report_week,
                "entity": sheet_name,
                "metrics": metrics,
                "evidence_id": evidence_id
            })
    
    return facts, evidence
