from typing import List, Dict, Any, Optional
import json
import uuid
from datetime import datetime

class A2UIService:
    """
    Service to generate A2UI (Agent to UI) protocol messages.
    Follows the Google A2UI v0.8 specification.
    """

    @staticmethod
    def create_surface_update(surface_id: str, components: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Creates a 'surfaceUpdate' message to define UI structure.
        """
        return {
            "surfaceUpdate": {
                "surfaceId": surface_id,
                "components": components
            }
        }

    @staticmethod
    def create_data_model_update(surface_id: str, contents: List[Dict[str, Any]], path: str = "/") -> Dict[str, Any]:
        """
        Creates a 'dataModelUpdate' message to update state.
        """
        return {
            "dataModelUpdate": {
                "surfaceId": surface_id,
                "path": path,
                "contents": contents
            }
        }

    @staticmethod
    def create_begin_rendering(surface_id: str, root_id: str, styles: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Creates a 'beginRendering' message to signal readiness.
        """
        payload = {
            "surfaceId": surface_id,
            "root": root_id
        }
        if styles:
            payload["styles"] = styles
        return {
            "beginRendering": payload
        }

    # --- Component Helpers ---

    @staticmethod
    def text(text_content: str, usage_hint: Optional[str] = None) -> Dict[str, Any]:
        """Creates a Text component definition."""
        comp = {"text": {"literalString": text_content}}
        if usage_hint:
            comp["usageHint"] = usage_hint
        return {"Text": comp}

    @staticmethod
    def button(label: str, action_name: str, context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Creates a Button component definition."""
        btn = {
            "label": {"literalString": label},
            "action": {"name": action_name}
        }
        if context:
            btn["action"]["context"] = context
        return {"Button": btn}

    @staticmethod
    def card(child_id: str) -> Dict[str, Any]:
        """Creates a Card component definition."""
        return {"Card": {"child": child_id}}

    @staticmethod
    def column(children_ids: List[str]) -> Dict[str, Any]:
        """Creates a Column component definition."""
        return {"Column": {"children": {"explicitList": children_ids}}}

    @staticmethod
    def row(children_ids: List[str], alignment: str = "start") -> Dict[str, Any]:
        """Creates a Row component definition."""
        return {"Row": {"alignment": alignment, "children": {"explicitList": children_ids}}}
    
    @staticmethod
    def text_field(label: str, bound_path: str) -> Dict[str, Any]:
        """Creates a TextField component definition bound to a data path."""
        return {
            "TextField": {
                "label": {"literalString": label},
                "text": {"path": bound_path}
            }
        }

    # --- Use Case Generators ---

    @staticmethod
    def generate_welcome_card(surface_id: str = "main") -> List[Dict[str, Any]]:
        """
        Generates a sample welcome card using A2UI.
        Returns a list of A2UI messages (JSON objects).
        """
        root_id = "root-column"
        
        # 1. Structure
        components = [
            {"id": root_id, "component": A2UIService.column(["welcome-card"])},
            {"id": "welcome-card", "component": A2UIService.card("card-content")},
            {"id": "card-content", "component": A2UIService.column(["title", "desc", "action-row"])},
            {"id": "title", "component": A2UIService.text("Agentic Interface Active", "h2")},
            {"id": "desc", "component": A2UIService.text("This UI is generated server-side using the A2UI protocol.")},
            {"id": "action-row", "component": A2UIService.row(["demo-btn"])},
            {"id": "demo-btn", "component": A2UIService.button("Run Demo", "demo_action")}
        ]

        return [
            A2UIService.create_surface_update(surface_id, components),
            A2UIService.create_begin_rendering(surface_id, root_id)
        ]
