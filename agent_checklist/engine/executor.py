from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from pydantic import BaseModel

from agent_checklist.domain import SkillName
from agent_checklist.llm.client import LLMClient
from agent_checklist.memory.models import ResearchState
from agent_checklist.skills.definitions import get_skill_definition


@dataclass(frozen=True, slots=True)
class Executor:
    """Loads skill definitions, renders prompts, and invokes the LLM client."""

    client: LLMClient

    def run_skill(
        self,
        *,
        skill_name: SkillName,
        state: ResearchState,
        context: Mapping[str, object] | None = None,
    ) -> BaseModel:
        definition = get_skill_definition(skill_name)
        prompt_context: dict[str, object] = {"state": state}
        if context:
            prompt_context.update(context)
        prompt = definition.render_prompt(prompt_context)
        return self.client.invoke(prompt=prompt, output_model=definition.output_model)
