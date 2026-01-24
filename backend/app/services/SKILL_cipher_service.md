# Agent Skill: Cipher Memory & Skill Management

**Version:** 1.0.0
**Model:** Any (Tool-based execution)
**Thread Type:** Base Thread (B) - Persistent state service

## Description

This skill enables agents to interact with the Byterover Cipher memory system. It provides a unified interface for storing memories, managing user preferences, learning new skills, and searching stored knowledge. The Cipher service is the "long-term memory" of the PMOVES-DoX system.

**When to use:**
- Storing facts extracted from documents for later retrieval
- Saving user preferences across sessions
- Registering new agent skills dynamically
- Searching previously stored memories by category or query
- Building a knowledge base from document processing results

**Why it exists:**
Agents require persistent state that survives session boundaries. The Cipher service provides a unified API that abstracts the underlying database (SQLite or Supabase), enabling agents to "remember" context across conversations and document processing runs.

## Core Principles

1. **Database Agnostic:** All operations go through the database factory, supporting both SQLite and Supabase backends.
2. **Graceful Fallback:** If a method is not implemented in the current DB adapter, warnings are logged but no exceptions are raised.
3. **Category-Based Organization:** Memories are organized by category (fact, preference, skill) for efficient retrieval.
4. **Context Preservation:** All memory operations support optional context metadata for provenance tracking.

## Capabilities

- **Memory Storage:** Store arbitrary content with category and context
- **Memory Search:** Query stored memories by category or text search
- **Skill Registry:** List and register agent skills
- **Preference Management:** Store and retrieve user-specific preferences
- **Fact Extraction:** Specialized wrapper for storing extracted facts

## Tools

The following static methods are available on the `CipherService` class:

| Method | Description | Usage |
|--------|-------------|-------|
| `add_memory(category, content, context)` | Store a generic memory | `CipherService.add_memory("fact", {"key": "value"}, {"source": "doc"})` |
| `search_memory(category, q)` | Search memories by category/query | `CipherService.search_memory(category="fact", q="revenue")` |
| `list_skills()` | List all enabled skills | `skills = CipherService.list_skills()` |
| `add_fact(content, source)` | Store a fact (convenience wrapper) | `CipherService.add_fact({"entity": "ACME", "value": "$1M"}, "pdf")` |
| `add_preference(key, value, user_id)` | Store user preference | `CipherService.add_preference("theme", "dark", "user123")` |
| `get_preferences(user_id)` | Get all user preferences | `prefs = CipherService.get_preferences("user123")` |
| `learn_skill(name, description, workflow)` | Register a new skill | `CipherService.learn_skill("summarize", "Summarizes text", workflow_dict)` |

## Context Priming

Before using the Cipher service:
1. Ensure the database is initialized via `database_factory.get_db_interface()`
2. Understand the current backend: `DB_BACKEND=sqlite` or `DB_BACKEND=supabase`
3. Note that not all adapters implement all methods - check logs for warnings
4. For dual-write mode, set `SUPABASE_DUAL_WRITE=true`

## Memory Categories

| Category | Purpose | Example Content |
|----------|---------|-----------------|
| `fact` | Extracted facts from documents | `{"entity": "ACME Corp", "metric": "revenue", "value": "$2.5M"}` |
| `preference` | User settings and preferences | `{"key": "theme", "value": "dark"}` |
| `skill` | Registered agent skills | `{"name": "summarize", "description": "..."}` |
| `context` | Session/conversation context | `{"session_id": "abc", "topic": "Q4 analysis"}` |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_BACKEND` | Database backend selection | `sqlite` |
| `SUPABASE_URL` | Supabase project URL | - |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | - |
| `SUPABASE_DUAL_WRITE` | Write to both SQLite and Supabase | `false` |

## Integration Example

```python
from app.services.cipher_service import CipherService

# Store a fact extracted from a PDF
fact_id = CipherService.add_fact(
    content={
        "entity": "Quarterly Revenue",
        "value": "$2.5 million",
        "period": "Q4 2024"
    },
    source="financial_report.pdf"
)

# Search for revenue-related facts
results = CipherService.search_memory(
    category="fact",
    q="revenue"
)

# Store user preference
CipherService.add_preference(
    key="default_model",
    value="gemini-2.5-flash",
    user_id="agent-zero"
)

# Register a new skill
skill_id = CipherService.learn_skill(
    name="extract_tables",
    description="Extract tables from PDF documents",
    workflow={
        "steps": ["upload", "process", "extract", "validate"],
        "tools": ["docling", "pandas"]
    }
)

# List available skills
skills = CipherService.list_skills()
for skill in skills:
    print(f"Skill: {skill['name']} - {skill['description']}")
```

## Database Adapter Interface

The Cipher service expects the following methods on the database adapter:

```python
# Memory operations
db.add_memory(category: str, content: Dict, context: Optional[Dict]) -> str
db.search_memory(category: Optional[str], q: Optional[str]) -> List[Dict]

# Skill operations
db.list_skills(enabled_only: bool) -> List[Dict]
db.register_skill(name: str, description: str, config: Dict, workflow: Dict) -> str

# Preference operations
db.set_user_pref(user_id: str, key: str, value: Any) -> None
db.get_user_prefs(user_id: str) -> Dict
```

## Cookbook (Progressive Disclosure)

Refer to the following for advanced patterns:
- **Memory Indexing:** Memories can be vector-indexed for semantic search (see SearchIndex)
- **Skill Workflows:** Workflow dicts can contain DAG structures for multi-step execution
- **Context Inheritance:** Child memories can reference parent contexts via the context dict
- **Supabase Migration:** Set `SUPABASE_DUAL_WRITE=true` during migration to write to both backends
