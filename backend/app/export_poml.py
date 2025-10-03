from __future__ import annotations

from typing import Dict, List, Optional
from pathlib import Path


def esc(text: str) -> str:
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def build_poml(
    doc: Dict,
    apis: List[Dict],
    tags: List[Dict],
    logs: List[Dict],
    markdown_path: Optional[Path] = None,
    chr_csv_path: Optional[Path] = None,
    variant: str = "generic",
) -> str:
    title = esc(doc.get('title') or Path(doc.get('path','')).name)
    lines: List[str] = []
    lines.append("<poml>")
    # Role + system guidance
    if variant == "troubleshoot":
        lines.append("  <role>You are a pragmatic SRE for an LMS platform. Diagnose succinctly with evidence.</role>")
        lines.append("  <system-msg>PMOVES_DoX troubleshooting mode: prioritize error codes, components, timestamps, and likely root causes.</system-msg>")
        lines.append(f"  <task>Identify causes and fixes related to: {title}. Use logs, APIs, and tags to justify answers.</task>")
    elif variant == "catalog":
        lines.append("  <role>You are a precise technical writer. Generate concise catalogs from source artifacts.</role>")
        lines.append("  <system-msg>PMOVES_DoX catalog mode: summarize APIs, key tags, and references for quick discovery.</system-msg>")
        lines.append(f"  <task>Produce a compact catalog for: {title}. Include endpoint summaries and notable tags.</task>")
    else:
        lines.append("  <role>You are a precise analyst. Prefer terse answers with citations.</role>")
        lines.append("  <system-msg>PMOVES_DoX: document analysis and structured extraction for LMS/enterprise artifacts.</system-msg>")
        lines.append(f"  <task>Answer questions about: {title}. Use provided APIs, tags, logs, and tables as sources.</task>")

    # Optional resources: document (markdown) and CHR table
    if markdown_path and markdown_path.exists():
        rel = str(markdown_path)
        lines.append(f"  <document src=\"{esc(rel)}\" parser=\"markdown\" />")
    if chr_csv_path and chr_csv_path.exists():
        relc = str(chr_csv_path)
        lines.append(f"  <table src=\"{esc(relc)}\" parser=\"csv\" maxRecords=\"20\" syntax=\"csv\" />")

    # Examples based on tags and APIs
    if tags:
        lines.append("  <examples>")
        if variant == "troubleshoot" and logs:
            for l in logs[:3]:
                code = esc(str(l.get('code') or ''))
                comp = esc(str(l.get('component') or ''))
                msg = esc(str(l.get('message') or ''))
                lines.append("    <example>")
                lines.append(f"      <input>Why does code {code} occur in component {comp}?</input>")
                lines.append(f"      <output>Describe likely cause and a fix. Cite the log message: {msg[:120]}...</output>")
                lines.append("    </example>")
        else:
            for t in tags[:3]:
                tag = esc(t.get('tag',''))
                lines.append("    <example>")
                lines.append(f"      <input>Find references to {tag}</input>")
                lines.append("      <output>Provide a one-line answer and cite log/API/table where found.</output>")
                lines.append("    </example>")
        lines.append("  </examples>")

    # APIs resource list (truncate for brevity)
    if apis:
        lines.append("  <resource type=\"apis\">")
        for a in apis[:50]:
            lines.append(f"    <api method=\"{esc(a.get('method',''))}\" path=\"{esc(a.get('path',''))}\">{esc(a.get('summary') or '')}</api>")
        lines.append("  </resource>")
    # Logs resource (truncate)
    if logs:
        lines.append("  <resource type=\"logs\">")
        for l in logs[:100]:
            lines.append(f"    <log ts=\"{esc(str(l.get('ts') or ''))}\" level=\"{esc(str(l.get('level') or ''))}\" code=\"{esc(str(l.get('code') or ''))}\">{esc(l.get('message') or '')}</log>")
        lines.append("  </resource>")

    # Output schema (JSON)
    lines.append("  <output-schema parser=\"json\">")
    lines.append("  {\n    \"type\": \"object\",\n    \"properties\": {\n      \"answer\": { \"type\": \"string\" },\n      \"citations\": { \"type\": \"array\", \"items\": { \"type\": \"string\" } }\n    }\n  }")
    lines.append("  </output-schema>")

    # Small stylesheet for tables
    lines.append("  <stylesheet>{\n    \"table\": { \"syntax\": \"csv\", \"writerOptions\": { \"csvHeader\": false, \"csvSeparator\": \" \" } }\n  }</stylesheet>")
    lines.append("</poml>")
    return "\n".join(lines)
