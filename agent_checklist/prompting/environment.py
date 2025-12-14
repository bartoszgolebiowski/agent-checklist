from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


_TEMPLATE_ROOT = Path(__file__).parent / "jinja"


@lru_cache(maxsize=1)
def get_prompt_environment() -> Environment:
    """Builds (and caches) the shared Jinja2 environment for prompts."""

    loader = FileSystemLoader(str(_TEMPLATE_ROOT))
    env = Environment(
        loader=loader, trim_blocks=True, lstrip_blocks=True, autoescape=False
    )
    env.globals.update({"TEMPLATE_ROOT": str(_TEMPLATE_ROOT)})
    return env
