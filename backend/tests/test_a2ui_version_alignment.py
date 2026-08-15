"""The advertised A2UI extension version must match the dialect we actually emit.

DoX advertises an A2UI A2A extension in its AgentCard and, separately, generates
A2UI messages in A2UIService. Nothing structurally ties those two together, so
they can drift: an A2A client that honours the advertisement would fetch the
advertised catalog and then fail to parse what we send.

The two dialects differ observably:

    v0.8   {"surfaceUpdate": ...}    {"Text": {"text": {"literalString": ...},
                                               "usageHint": ...}}
    v0.9   {"updateComponents": ...} {"component": "Text", "text": ...,
                                               "variant": ...}

These tests derive the version from each side and assert they agree, rather than
hard-coding one expected value -- so they keep working if DoX later moves to v0.9,
and fail if only one side moves.

The advertised side is read from the source with `ast` rather than by importing
the router. Importing it pulls app.auth, which raises unless python-jose is
installed, and a test that skips itself in that situation is a gate that cannot
fail. Parsing the literal keeps this check running everywhere.
"""
import ast
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest

from app.services.a2ui_service import A2UIService

A2UI_EXTENSION_PREFIX = "https://a2ui.org/a2a-extension/a2ui/"
A2A_ROUTER = BACKEND_DIR / "app" / "api" / "routers" / "a2a.py"


def _literal_list(node) -> list:
    if not isinstance(node, ast.List):
        return []
    return [el.value for el in node.elts if isinstance(el, ast.Constant)]


def _advertised() -> tuple:
    """(uri, supportedCatalogIds) for the A2UI capability, read from the source."""
    assert A2A_ROUTER.is_file(), f"missing {A2A_ROUTER}"
    tree = ast.parse(A2A_ROUTER.read_text(encoding="utf-8"))

    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = getattr(func, "id", None) or getattr(func, "attr", None)
        if name != "AgentCapability":
            continue
        kwargs = {kw.arg: kw.value for kw in node.keywords}
        uri = kwargs.get("uri")
        if not (isinstance(uri, ast.Constant) and A2UI_EXTENSION_PREFIX in str(uri.value)):
            continue

        catalog_ids = []
        params = kwargs.get("params")
        if isinstance(params, ast.Dict):
            for key, value in zip(params.keys, params.values):
                if isinstance(key, ast.Constant) and key.value == "supportedCatalogIds":
                    catalog_ids = _literal_list(value)
        found.append((uri.value, catalog_ids))

    assert found, (
        "no A2UI extension capability found in "
        f"{A2A_ROUTER.relative_to(BACKEND_DIR)}; expected an AgentCapability whose uri "
        f"begins with {A2UI_EXTENSION_PREFIX}"
    )
    assert len(found) == 1, f"expected exactly one A2UI capability, found {len(found)}"
    return found[0]


def _generated_dialect() -> str:
    """Infer the A2UI version A2UIService actually emits, from its own output."""
    surface = A2UIService.create_surface_update("surface-1", [])
    begin = A2UIService.create_begin_rendering("surface-1", "root")
    text = A2UIService.text("hello", usage_hint="h3")

    if "surfaceUpdate" in surface and "beginRendering" in begin:
        dialect = "v0.8"
    elif "updateComponents" in surface:
        dialect = "v0.9"
    else:
        pytest.fail(f"unrecognised message envelope: {sorted(surface)} / {sorted(begin)}")

    # The component shape must agree with the envelope, or the generator is itself mixed.
    nested_v08 = "Text" in text and "literalString" in str(text)
    flat_v09 = text.get("component") == "Text"
    if dialect == "v0.8":
        assert nested_v08 and not flat_v09, (
            f"envelope is v0.8 but the component shape is not the v0.8 nested form: {text}"
        )
    else:
        assert flat_v09 and not nested_v08, (
            f"envelope is v0.9 but the component shape is not the v0.9 flat form: {text}"
        )
    return dialect


def test_advertised_extension_version_matches_generated_dialect():
    uri, _ = _advertised()
    advertised = uri[len(A2UI_EXTENSION_PREFIX):].strip("/")
    generated = _generated_dialect()
    assert advertised == generated, (
        f"AgentCard advertises A2UI {advertised} but A2UIService emits {generated}. "
        "A client honouring the advertisement would mis-parse our messages. "
        "Move both, or neither."
    )


def test_supported_catalog_ids_reference_the_advertised_version():
    uri, catalog_ids = _advertised()
    advertised = uri[len(A2UI_EXTENSION_PREFIX):].strip("/")
    # "v0.8" in the extension uri is spelled "v0_8" in specification paths.
    expected_fragment = advertised.replace(".", "_")

    assert catalog_ids, "A2UI capability advertises no supportedCatalogIds"
    mismatched = [c for c in catalog_ids if expected_fragment not in c]
    assert not mismatched, (
        f"advertised extension is {advertised}, so catalog ids should reference "
        f"{expected_fragment}; these do not: {mismatched}"
    )
