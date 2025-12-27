import typer
import uvicorn
import asyncio
import os
import sys
import json
from pathlib import Path
from app.services.cipher_service import CipherService

app = typer.Typer(help="PMOVES-DoX Tactical CLI (tac)")


# Create subgroups
memory_app = typer.Typer(help="Manage Cipher Memory")
skills_app = typer.Typer(help="Manage Skills Registry")
app.add_typer(memory_app, name="memory")
app.add_typer(skills_app, name="skills")

@app.command()
def start(
    host: str = "127.0.0.1", 
    port: int = 8484, 
    reload: bool = True
):
    """Start the FastAPI backend server."""
    typer.echo(f"🚀 Launching TAC Backend on http://{host}:{port}")
    uvicorn.run("app.main:app", host=host, port=port, reload=reload)

@app.command()
def db_status():
    """Check database connection status."""
    from app.database_factory import get_db_interface
    try:
        db = get_db_interface()
        # Check backend type roughly logic
        backend_type = getattr(db, "backend", "unknown")
        print(f"✅ Database connection successful (Backend: {backend_type})")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

# --- Memory Commands ---
@memory_app.command("add")
def memory_add(category: str, content: str, context: str = "{}"):
    """Add a new memory item."""
    try:
        content_json = json.loads(content)
        context_json = json.loads(context)
        mid = CipherService.add_memory(category, content_json, context_json)
        print(f"✅ Memory added: {mid}")
    except json.JSONDecodeError:
        print("❌ Error: Valid JSON required for content/context")

@memory_app.command("search")
def memory_search(category: str = None, q: str = None):
    """Search memory items."""
    results = CipherService.search_memory(category=category, q=q)
    print(f"Found {len(results)} items:")
    for r in results:
        print(f" - [{r['category']}] {r['id']} (Created: {r['created_at']})")
        print(f"   Content: {json.dumps(r['content'])[:100]}...")

# --- Skills Commands ---
@skills_app.command("list")
def skills_list():
    """List registered skills."""
    skills = CipherService.list_skills()
    print(f"Found {len(skills)} skills:")
    for s in skills:
        status = "🟢" if s['enabled'] else "🔴"
        print(f" {status} {s['name']}: {s['description']}")

if __name__ == "__main__":
    app()
