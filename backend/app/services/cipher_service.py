from typing import Dict, List, Optional, Any
from app.database_factory import get_db_interface
import logging

LOGGER = logging.getLogger(__name__)

class CipherService:
    @staticmethod
    def _get_db():
        return get_db_interface()

    @staticmethod
    def add_memory(category: str, content: Dict, context: Optional[Dict] = None) -> str:
        """Stores a generic memory."""
        db = CipherService._get_db()
        if hasattr(db, "add_memory"):
            return db.add_memory(category, content, context)
        LOGGER.warning("add_memory not implemented in current DB adapter")
        return ""

    @staticmethod
    def search_memory(category: Optional[str] = None, q: Optional[str] = None) -> List[Dict]:
        """Searches memory."""
        db = CipherService._get_db()
        if hasattr(db, "search_memory"):
            return db.search_memory(category=category, q=q)
        return []

    @staticmethod
    def list_skills() -> List[Dict]:
        """Lists all enabled skills."""
        db = CipherService._get_db()
        if hasattr(db, "list_skills"):
            return db.list_skills(enabled_only=True)
        return []

    # --- Legacy/Specific Wrappers ---

    @staticmethod
    def add_fact(content: Dict, source: str = "user_input") -> str:
        return CipherService.add_memory("fact", content, {"source": source})

    @staticmethod
    def add_preference(key: str, value: Any, user_id: str) -> None:
        db = CipherService._get_db()
        if hasattr(db, "set_user_pref"):
            db.set_user_pref(user_id, key, value)
        else:
            LOGGER.warning("set_user_pref not implemented in current DB adapter")

    @staticmethod
    def get_preferences(user_id: str) -> Dict:
        db = CipherService._get_db()
        if hasattr(db, "get_user_prefs"):
            return db.get_user_prefs(user_id)
        return {}

    @staticmethod
    def learn_skill(name: str, description: str, workflow: Dict) -> str:
        db = CipherService._get_db()
        if hasattr(db, "register_skill"):
            return db.register_skill(name, description, {}, workflow)
        return ""
