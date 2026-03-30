"""Tests for the LLM vendor tool."""

from __future__ import annotations

from scripts.llm_vendor import extract_used_symbols, rewrite_imports


def test_rewrite_imports_shared_to_local():
    source = """from shared.config import get_model, PROFILES_DIR
from shared.operator import get_system_prompt_fragment
import json
"""
    result = rewrite_imports(source, {"shared.config": "config", "shared.operator": "operator"})
    assert "from .config import get_model, PROFILES_DIR" in result
    assert "from .operator import get_system_prompt_fragment" in result
    assert "import json" in result
    assert "shared" not in result


def test_extract_used_symbols():
    source = """from shared.config import get_model, PROFILES_DIR, QDRANT_URL
x = get_model("fast")
y = PROFILES_DIR / "test"
"""
    used = extract_used_symbols(
        source, "shared.config", ["get_model", "PROFILES_DIR", "QDRANT_URL"]
    )
    assert "get_model" in used
    assert "PROFILES_DIR" in used
    assert "QDRANT_URL" not in used
