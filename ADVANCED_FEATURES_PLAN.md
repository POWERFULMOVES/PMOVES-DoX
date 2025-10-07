# Advanced PDF Processing Features - Implementation Plan

## Overview

This document outlines advanced PDF processing capabilities using IBM Granite Docling and the Docling library for enterprise-grade document analysis.

---

## Phase 1: Enhanced Layout Analysis (Current + Immediate Next Steps)

### Current Implementation ✓
- Basic PDF to text conversion
- Table extraction with structure preservation
- OCR for scanned documents
- Bounding box coordinates for all elements
- Export to Markdown and JSON

### Immediate Enhancements

#### 1.1 Multi-Page Table Detection
**Goal**: Handle tables that span multiple pages

```python
# backend/app/ingestion/advanced_table_processor.py

from docling.document_converter import DocumentConverter
from typing import List, Dict
import pandas as pd

class AdvancedTableProcessor:
    """Process complex multi-page tables"""
    
    def detect_spanning_tables(self, doc) -> List[Dict]:
        """
        Detect and merge tables that span multiple pages
        Uses table position, column structure, and headers
        """
        tables = []
        previous_table = None
        
        for page_idx, page in enumerate(doc.pages):
            for table in page.tables:
                if self._is_continuation(previous_table, table):
                    # Merge with previous table
                    tables[-1]['dataframe'] = pd.concat([
                        tables[-1]['dataframe'],
                        table.export_to_dataframe()
                    ])
                    tables[-1]['pages'].append(page_idx)
                else:
                    # New table
                    tables.append({
                        'dataframe': table.export_to_dataframe(),
                        'pages': [page_idx],
                        'bbox': table.bbox,
                        'header_detected': self._detect_header(table)
                    })
                previous_table = table
        
        return tables
    
    def _is_continuation(self, prev_table, curr_table) -> bool:
        """Check if current table continues previous one"""
        if not prev_table:
            return False
        
        # Compare column structures
        prev_df = prev_table.export_to_dataframe()
        curr_df = curr_table.export_to_dataframe()
        
        # Check if columns match
        return list(prev_df.columns) == list(curr_df.columns)
    
    def _detect_header(self, table) -> bool:
        """Detect if table has a header row"""
        df = table.export_to_dataframe()
        if len(df) == 0:
            return False
        
        # Check if first row is different (header-like)
        first_row = df.iloc[0]
        return first_row.dtype == 'object'
```

#### 1.2 Chart and Graph Extraction
**Goal**: Extract data from charts, graphs, and visualizations

```python
# backend/app/ingestion/chart_processor.py

from docling.datamodel.base_models import Figure
import cv2
import numpy as np
from typing import Dict, List

class ChartProcessor:
    """Extract and analyze charts from PDFs"""
    
    async def process_charts(self, doc, artifacts_dir) -> List[Dict]:
        """
        Extract charts and attempt to extract underlying data
        """
        charts = []
        
        for fig_idx, figure in enumerate(doc.pictures):
            # Save figure as image
            img_path = artifacts_dir / f"chart_{fig_idx}.png"
            
            # Get figure properties
            chart_data = {
                'id': f"chart_{fig_idx}",
                'page': figure.prov[0].page if figure.prov else None,
                'bbox': figure.prov[0].bbox.as_tuple() if hasattr(figure.prov[0], 'bbox') else None,
                'image_path': str(img_path),
                'type': self._detect_chart_type(figure),
                'caption': self._extract_caption(figure),
                'extracted_data': None
            }
            
            # Attempt OCR on chart labels
            if hasattr(figure, 'image'):
                chart_data['extracted_data'] = self._extract_chart_data(figure.image)
            
            charts.append(chart_data)
        
        return charts
    
    def _detect_chart_type(self, figure) -> str:
        """Detect type of chart (bar, line, pie, etc.)"""
        # Use simple heuristics or ML model
        # This is a placeholder
        return "unknown"
    
    def _extract_caption(self, figure) -> str:
        """Extract figure caption"""
        # Look for nearby text elements
        return ""
    
    def _extract_chart_data(self, image) -> Dict:
        """Extract data points from chart using OCR and image processing"""
        # Use OCR on axis labels and values
        # This would integrate with Tesseract or similar
        return {}
```

#### 1.3 Formula and Equation Detection
**Goal**: Detect and preserve mathematical formulas

```python
# backend/app/ingestion/formula_processor.py

import re
from typing import List, Dict

class FormulaProcessor:
    """Detect and process mathematical formulas"""
    
    def extract_formulas(self, doc) -> List[Dict]:
        """
        Extract mathematical formulas and equations
        Docling can detect equation blocks
        """
        formulas = []
        
        for page_idx, page in enumerate(doc.pages):
            # Look for equation elements
            for item in page.elements:
                if hasattr(item, 'label') and item.label == 'equation':
                    formulas.append({
                        'page': page_idx,
                        'content': item.text,
                        'latex': self._convert_to_latex(item.text),
                        'bbox': item.bbox if hasattr(item, 'bbox') else None
                    })
        
        return formulas
    
    def _convert_to_latex(self, text: str) -> str:
        """Convert text representation to LaTeX"""
        # Use simple pattern matching or ML model
        return text
```

---

## Phase 2: Advanced Text Analysis

#### 2.1 Named Entity Recognition (NER)
**Goal**: Extract companies, people, dates, locations

```python
# backend/app/analysis/ner_processor.py

from typing import List, Dict
import spacy

class NERProcessor:
    """Extract named entities from document text"""
    
    def __init__(self):
        # Load spaCy model
        self.nlp = spacy.load("en_core_web_sm")
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract named entities from text
        Returns categorized entities
        """
        doc = self.nlp(text)
        
        entities = {
            'PERSON': [],
            'ORG': [],
            'DATE': [],
            'MONEY': [],
            'PERCENT': [],
            'LOC': []
        }
        
        for ent in doc.ents:
            if ent.label_ in entities:
                entities[ent.label_].append(ent.text)
        
        return entities
```

#### 2.2 Section Hierarchy Detection
**Goal**: Understand document structure (headers, sections, subsections)

```python
# backend/app/analysis/structure_processor.py

from typing import List, Dict
from docling.datamodel.base_models import TextElement

class DocumentStructureProcessor:
    """Analyze document structure and hierarchy"""
    
    def build_hierarchy(self, doc) -> Dict:
        """
        Build hierarchical structure of document
        Identifies sections, subsections, paragraphs
        """
        structure = {
            'title': self._extract_title(doc),
            'sections': []
        }
        
        current_section = None
        
        for item in doc.texts:
            # Docling can identify heading levels
            if hasattr(item, 'label'):
                if item.label.startswith('heading'):
                    level = int(item.label.replace('heading-', ''))
                    
                    section = {
                        'level': level,
                        'title': item.text,
                        'content': [],
                        'subsections': []
                    }
                    
                    if level == 1:
                        structure['sections'].append(section)
                        current_section = section
                    elif current_section:
                        current_section['subsections'].append(section)
                
                elif item.label == 'paragraph' and current_section:
                    current_section['content'].append(item.text)
        
        return structure
    
    def _extract_title(self, doc) -> str:
        """Extract document title"""
        # Usually first heading or title element
        for item in doc.texts:
            if hasattr(item, 'label') and item.label == 'title':
                return item.text
        return "Untitled"
```

#### 2.3 Key Information Extraction
**Goal**: Extract specific business metrics automatically

```python
# backend/app/analysis/metric_extractor.py

import re
from typing import Dict, List, Tuple

class BusinessMetricExtractor:
    """Extract business metrics using patterns and context"""
    
    def __init__(self):
        self.patterns = {
            'revenue': [
                r'revenue[:\s]+\$?\s*([0-9,.]+[KMB]?)',
                r'sales[:\s]+\$?\s*([0-9,.]+[KMB]?)',
                r'\$([0-9,.]+[KMB]?)\s+in\s+revenue'
            ],
            'growth': [
                r'growth[:\s]+([0-9.]+)%',
                r'increase[d]?\s+by\s+([0-9.]+)%',
                r'([0-9.]+)%\s+growth'
            ],
            'margin': [
                r'margin[:\s]+([0-9.]+)%',
                r'([0-9.]+)%\s+margin'
            ]
        }
    
    def extract_metrics(self, text: str, context_window: int = 50) -> List[Dict]:
        """
        Extract metrics with surrounding context
        """
        metrics = []
        
        for metric_type, patterns in self.patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    # Get context around match
                    start = max(0, match.start() - context_window)
                    end = min(len(text), match.end() + context_window)
                    context = text[start:end]
                    
                    metrics.append({
                        'type': metric_type,
                        'value': match.group(1),
                        'context': context,
                        'position': match.start()
                    })
        
        return metrics
```

---

## Phase 3: Advanced Table Processing

#### 3.1 Complex Table Structures
**Goal**: Handle merged cells, nested tables, multi-level headers

```python
# backend/app/ingestion/complex_table_processor.py

class ComplexTableProcessor:
    """Handle complex table structures"""
    
    def process_merged_cells(self, table_data) -> pd.DataFrame:
        """
        Handle tables with merged cells
        Docling provides cell span information
        """
        # Process cell spans
        # Forward-fill merged cells
        pass
    
    def detect_multi_level_headers(self, df: pd.DataFrame) -> Dict:
        """
        Detect and process multi-level column headers
        """
        if len(df) < 2:
            return {'levels': 1, 'headers': [df.columns.tolist()]}
        
        # Check if first few rows are headers
        header_rows = []
        for idx in range(min(3, len(df))):
            row = df.iloc[idx]
            if self._is_header_row(row):
                header_rows.append(row.tolist())
            else:
                break
        
        return {
            'levels': len(header_rows),
            'headers': header_rows
        }
    
    def _is_header_row(self, row) -> bool:
        """Check if row is likely a header"""
        # Headers usually have string values
        return row.dtype == 'object'
```

#### 3.2 Financial Statement Detection
**Goal**: Automatically identify and parse financial statements

```python
# backend/app/analysis/financial_statement_detector.py

class FinancialStatementDetector:
    """Detect and parse financial statements"""
    
    STATEMENT_TYPES = {
        'balance_sheet': ['assets', 'liabilities', 'equity'],
        'income_statement': ['revenue', 'expenses', 'net income'],
        'cash_flow': ['operating', 'investing', 'financing']
    }
    
    def detect_statement_type(self, table_df: pd.DataFrame) -> str:
        """
        Identify type of financial statement
        """
        columns_text = ' '.join([str(col).lower() for col in table_df.columns])
        table_text = ' '.join([str(cell).lower() for cell in table_df.values.flatten()])
        
        combined = columns_text + ' ' + table_text
        
        for stmt_type, keywords in self.STATEMENT_TYPES.items():
            matches = sum(1 for kw in keywords if kw in combined)
            if matches >= 2:
                return stmt_type
        
        return 'unknown'
    
    def parse_financial_statement(self, table_df: pd.DataFrame, stmt_type: str) -> Dict:
        """
        Extract structured data from financial statement
        """
        if stmt_type == 'income_statement':
            return self._parse_income_statement(table_df)
        elif stmt_type == 'balance_sheet':
            return self._parse_balance_sheet(table_df)
        else:
            return {}
    
    def _parse_income_statement(self, df: pd.DataFrame) -> Dict:
        """Parse income statement"""
        return {
            'revenue': self._find_value(df, 'revenue'),
            'expenses': self._find_value(df, 'expenses'),
            'net_income': self._find_value(df, 'net income')
        }
    
    def _find_value(self, df: pd.DataFrame, search_term: str) -> float:
        """Find a value in the dataframe"""
        # Search for term in first column, return value from last column
        for idx, row in df.iterrows():
            if search_term.lower() in str(row.iloc[0]).lower():
                try:
                    return float(str(row.iloc[-1]).replace(',', '').replace('$', ''))
                except:
                    pass
        return None
```

---

## Phase 4: Integration with RAG System

#### 4.1 Vector Store Integration
**Goal**: Store processed documents in your Supabase vector database

```python
# backend/app/vector_store.py

from supabase import create_client
import httpx
import os
from typing import List, Dict

class VectorStore:
    """Integration with Supabase vector store"""
    
    def __init__(self):
        self.supabase = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
        self.hf_api_key = os.getenv("HF_API_KEY")
        self.embedding_dim = 3584  # Your HF embedding dimension
    
    async def embed_text(self, text: str) -> List[float]:
        """Get embeddings from Hugging Face API"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api-inference.huggingface.co/models/{os.getenv('HF_MODEL')}",
                headers={"Authorization": f"Bearer {self.hf_api_key}"},
                json={"inputs": text}
            )
            return response.json()
    
    async def store_document_chunks(self, doc_id: str, chunks: List[Dict]):
        """
        Store document chunks with embeddings
        Each chunk includes text, metadata, and location info
        """
        for chunk in chunks:
            embedding = await self.embed_text(chunk['text'])
            
            self.supabase.table("document_chunks").insert({
                "document_id": doc_id,
                "chunk_text": chunk['text'],
                "chunk_type": chunk['type'],  # table, text, figure
                "page_number": chunk['page'],
                "bbox": chunk['bbox'],
                "metadata": chunk['metadata'],
                "embedding": embedding
            }).execute()
    
    async def hybrid_search(
        self, 
        query: str, 
        doc_types: List[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Perform hybrid search (semantic + keyword)
        """
        query_embedding = await self.embed_text(query)
        
        # Semantic search
        semantic_results = self.supabase.rpc(
            "match_document_chunks",
            {
                "query_embedding": query_embedding,
                "match_threshold": 0.7,
                "match_count": limit
            }
        ).execute()
        
        # Keyword search (full-text)
        keyword_results = self.supabase.table("document_chunks") \
            .select("*") \
            .text_search("chunk_text", query) \
            .limit(limit) \
            .execute()
        
        # Combine and rank results
        return self._merge_results(semantic_results.data, keyword_results.data)
    
    def _merge_results(self, semantic: List, keyword: List) -> List:
        """Merge and rank hybrid search results"""
        # Simple merge strategy - can be enhanced
        results = {}
        
        for idx, item in enumerate(semantic):
            item['semantic_rank'] = idx
            results[item['id']] = item
        
        for idx, item in enumerate(keyword):
            if item['id'] in results:
                results[item['id']]['keyword_rank'] = idx
            else:
                item['keyword_rank'] = idx
                results[item['id']] = item
        
        # Sort by combined rank
        sorted_results = sorted(
            results.values(),
            key=lambda x: (
                x.get('semantic_rank', 999) + 
                x.get('keyword_rank', 999)
            )
        )
        
        return sorted_results
```

#### 4.2 Semantic Chunking Strategy
**Goal**: Intelligent document chunking for better retrieval

```python
# backend/app/chunking/semantic_chunker.py

class SemanticChunker:
    """Intelligent document chunking"""
    
    def chunk_document(self, doc, max_chunk_size: int = 512) -> List[Dict]:
        """
        Chunk document semantically
        Preserves section boundaries and context
        """
        chunks = []
        
        # Chunk by sections first
        structure = self._get_document_structure(doc)
        
        for section in structure['sections']:
            # Each section is a chunk
            section_text = section['title'] + '\n' + ' '.join(section['content'])
            
            if len(section_text) > max_chunk_size:
                # Split large sections
                sub_chunks = self._split_text(section_text, max_chunk_size)
                for sub_chunk in sub_chunks:
                    chunks.append({
                        'text': sub_chunk,
                        'type': 'text',
                        'section': section['title'],
                        'page': section.get('page'),
                        'bbox': section.get('bbox')
                    })
            else:
                chunks.append({
                    'text': section_text,
                    'type': 'text',
                    'section': section['title'],
                    'page': section.get('page'),
                    'bbox': section.get('bbox')
                })
        
        # Add tables as separate chunks
        for table in doc.tables:
            chunks.append({
                'text': table.export_to_markdown(),
                'type': 'table',
                'page': table.prov[0].page if table.prov else None,
                'bbox': table.prov[0].bbox.as_tuple() if hasattr(table.prov[0], 'bbox') else None,
                'table_data': table.export_to_dataframe().to_dict('records')
            })
        
        return chunks
    
    def _split_text(self, text: str, max_size: int) -> List[str]:
        """Split text into chunks at sentence boundaries"""
        sentences = text.split('. ')
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < max_size:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
```

---

## Phase 5: Advanced Q&A Features

#### 5.1 Multi-hop Reasoning
**Goal**: Answer questions requiring multiple pieces of evidence

```python
# backend/app/qa/advanced_qa_engine.py

class AdvancedQAEngine:
    """Enhanced Q&A with multi-hop reasoning"""
    
    def __init__(self, db, vector_store):
        self.db = db
        self.vector_store = vector_store
    
    async def answer_complex_question(self, question: str) -> Dict:
        """
        Answer questions requiring multiple reasoning steps
        """
        # Step 1: Decompose question into sub-questions
        sub_questions = self._decompose_question(question)
        
        # Step 2: Answer each sub-question
        sub_answers = []
        for sub_q in sub_questions:
            answer = await self._answer_simple(sub_q)
            sub_answers.append(answer)
        
        # Step 3: Synthesize final answer
        final_answer = self._synthesize_answer(question, sub_answers)
        
        return final_answer
    
    def _decompose_question(self, question: str) -> List[str]:
        """Break complex question into simpler ones"""
        # Use LLM or rule-based system
        # Example: "What is the YoY revenue growth?" ->
        # ["What was revenue last year?", "What is revenue this year?"]
        return [question]  # Placeholder
    
    async def _answer_simple(self, question: str) -> Dict:
        """Answer a simple factual question"""
        # Use vector search to find relevant chunks
        results = await self.vector_store.hybrid_search(question, limit=5)
        
        return {
            'question': question,
            'evidence': results,
            'answer': self._extract_answer(results)
        }
    
    def _synthesize_answer(self, original_question: str, sub_answers: List[Dict]) -> Dict:
        """Combine sub-answers into final answer"""
        # Combine evidence from all sub-answers
        all_evidence = []
        for sa in sub_answers:
            all_evidence.extend(sa['evidence'])
        
        return {
            'question': original_question,
            'answer': self._generate_final_answer(original_question, sub_answers),
            'evidence': all_evidence,
            'reasoning_steps': [sa['question'] for sa in sub_answers]
        }
```

#### 5.2 Citation Highlighting
**Goal**: Show exact location of evidence in original PDF

```python
# backend/app/qa/citation_highlighter.py

from pathlib import Path
import fitz  # PyMuPDF

class CitationHighlighter:
    """Highlight citations in original PDF"""
    
    def create_highlighted_pdf(
        self, 
        original_pdf_path: Path,
        citations: List[Dict],
        output_path: Path
    ):
        """
        Create a copy of PDF with citations highlighted
        """
        doc = fitz.open(original_pdf_path)
        
        for citation in citations:
            if citation.get('page') and citation.get('bbox'):
                page = doc[citation['page'] - 1]  # 0-indexed
                
                # Create highlight annotation
                bbox = fitz.Rect(citation['bbox'])
                highlight = page.add_highlight_annot(bbox)
                highlight.set_colors(stroke=[1, 1, 0])  # Yellow
                highlight.update()
        
        doc.save(output_path)
        doc.close()
        
        return output_path
```

---

## Phase 6: Real-time Processing Pipeline

#### 6.1 Async Processing Queue
**Goal**: Handle large documents without blocking

```python
# backend/app/processing/async_processor.py

from celery import Celery
import asyncio

celery_app = Celery('pmoves_dox', broker='redis://localhost:6379')

@celery_app.task
def process_document_async(file_path: str, report_week: str):
    """Process document in background"""
    asyncio.run(_process_document(file_path, report_week))

async def _process_document(file_path: str, report_week: str):
    """Actual processing logic"""
    # Process PDF
    # Extract facts
    # Store in vector DB
    pass
```

#### 6.2 Progress Tracking
**Goal**: Show processing progress to user

```python
# backend/app/main.py - add endpoint

@app.get("/processing-status/{task_id}")
async def get_processing_status(task_id: str):
    """Get status of async processing task"""
    result = AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": result.state,
        "progress": result.info.get('progress', 0) if result.info else 0
    }
```

---

## Phase 7: Production Features

#### 7.1 Caching Strategy
```python
# backend/app/cache.py

from functools import lru_cache
import redis

class DocumentCache:
    """Cache processed documents"""
    
    def __init__(self):
        self.redis = redis.Redis(host='localhost', port=6379)
    
    def cache_document(self, doc_id: str, processed_data: Dict):
        """Cache processed document data"""
        self.redis.setex(
            f"doc:{doc_id}",
            3600,  # 1 hour TTL
            json.dumps(processed_data)
        )
    
    def get_cached(self, doc_id: str) -> Optional[Dict]:
        """Retrieve cached document"""
        data = self.redis.get(f"doc:{doc_id}")
        return json.loads(data) if data else None
```

#### 7.2 Error Handling and Retry Logic
```python
# backend/app/processing/error_handler.py

from tenacity import retry, stop_after_attempt, wait_exponential

class RobustProcessor:
    """Process documents with retry logic"""
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def process_with_retry(self, file_path: Path):
        """Process with automatic retry on failure"""
        try:
            return await self._process(file_path)
        except Exception as e:
            logging.error(f"Processing failed: {e}")
            raise
```

---

## Implementation Priority

### High Priority (Implement Next)
1. Multi-page table detection
2. Vector store integration
3. Semantic chunking
4. Chart extraction basics

### Medium Priority
5. NER and entity extraction
6. Financial statement detection
7. Advanced metric extraction
8. Citation highlighting

### Lower Priority (Nice to Have)
9. Multi-hop reasoning
10. Async processing queue
11. Formula detection
12. Progress tracking

---

## Testing Strategy

### Unit Tests
```python
# backend/tests/test_pdf_processor.py

import pytest
from app.ingestion.pdf_processor import process_pdf

@pytest.mark.asyncio
async def test_pdf_processing():
    """Test basic PDF processing"""
    result = await process_pdf(
        Path("test_files/sample.pdf"),
        "2025-W40",
        Path("test_artifacts")
    )
    facts, evidence = result
    assert len(facts) > 0
    assert len(evidence) > 0
```

### Integration Tests
```python
# backend/tests/test_integration.py

@pytest.mark.asyncio
async def test_end_to_end_flow():
    """Test complete document processing flow"""
    # Upload document
    # Process it
    # Ask question
    # Verify answer with citations
    pass
```

---

## Performance Optimization

### Batch Processing
```python
async def process_multiple_documents(file_paths: List[Path]):
    """Process multiple documents concurrently"""
    tasks = [process_pdf(fp, "", artifacts_dir) for fp in file_paths]
    return await asyncio.gather(*tasks)
```

### Model Optimization
- Use quantized versions of Granite model for faster inference
- Implement model caching
- Use GPU acceleration when available

---

## Deployment Considerations

### Docker Setup
```dockerfile
# Dockerfile
FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . /app
WORKDIR /app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables
```bash
# .env
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
HF_API_KEY=your-huggingface-key
HF_MODEL=your-embedding-model
REDIS_URL=redis://localhost:6379
```

---

## Success Metrics

- **Processing Speed**: < 10 seconds per page
- **Table Accuracy**: > 95% correct extraction
- **Chart Detection**: > 90% detection rate
- **Q&A Accuracy**: > 90% correct answers
- **Citation Precision**: 100% accurate location tracking

---

## Next Steps

1. Review this plan with team
2. Set up development environment
3. Implement Phase 1 features
4. Test with real documents
5. Iterate based on feedback
