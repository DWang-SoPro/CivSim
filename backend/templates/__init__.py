"""文明模板与行动类型定义。"""

from backend.templates.civilizations import (
    CIVILIZATION_TEMPLATES,
    get_template,
    list_templates,
    load_civ_state,
    validate_production_relations,
)

__all__ = [
    "CIVILIZATION_TEMPLATES",
    "get_template",
    "list_templates",
    "load_civ_state",
    "validate_production_relations",
]
