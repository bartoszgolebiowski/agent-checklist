from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Type

from pydantic import BaseModel

from agent_checklist.domain import SkillName
from agent_checklist.prompting.environment import get_prompt_environment
from agent_checklist.skills import models as skill_models


@dataclass(frozen=True, slots=True)
class SkillDefinition:
    """Declarative metadata for every available LLM skill."""

    name: SkillName
    template_path: str
    output_model: Type[BaseModel]
    description: str

    def render_prompt(self, context: Mapping[str, object]) -> str:
        env = get_prompt_environment()
        template = env.get_template(self.template_path)
        return template.render(**context)


_SKILL_DEFINITIONS: Dict[SkillName, SkillDefinition] = {
    SkillName.GENERATE_INITIAL_CHECKLIST: SkillDefinition(
        name=SkillName.GENERATE_INITIAL_CHECKLIST,
        template_path="skills/generate_initial_checklist.j2",
        output_model=skill_models.GenerateInitialChecklistOutput,
        description="Create a measurable checklist from the user's description.",
    ),
    SkillName.GENERATE_REFINEMENT_QUESTIONS: SkillDefinition(
        name=SkillName.GENERATE_REFINEMENT_QUESTIONS,
        template_path="skills/generate_refinement_questions.j2",
        output_model=skill_models.GenerateRefinementQuestionsOutput,
        description="Ask up to three high-value refinement questions.",
    ),
    SkillName.INCORPORATE_REFINEMENTS: SkillDefinition(
        name=SkillName.INCORPORATE_REFINEMENTS,
        template_path="skills/incorporate_refinements.j2",
        output_model=skill_models.IncorporateRefinementsOutput,
        description="Adjust the checklist based on user feedback.",
    ),
    SkillName.INTERPRET_PROGRESS_UPDATE: SkillDefinition(
        name=SkillName.INTERPRET_PROGRESS_UPDATE,
        template_path="skills/interpret_progress_update.j2",
        output_model=skill_models.InterpretProgressUpdateOutput,
        description="Map user input to checklist progress and context logs.",
    ),
    SkillName.GENERATE_COMPLETION_SUMMARY: SkillDefinition(
        name=SkillName.GENERATE_COMPLETION_SUMMARY,
        template_path="skills/completion_summary.j2",
        output_model=skill_models.CompletionSummaryOutput,
        description="Summarize the completed work using checklist data and logs.",
    ),
}


def get_skill_definition(name: SkillName) -> SkillDefinition:
    """Fetches the immutable skill definition for the provided name."""

    definition = _SKILL_DEFINITIONS.get(name)
    if definition is None:
        raise KeyError(f"Skill definition not found for {name}")
    return definition


ALL_SKILLS: list[SkillDefinition] = list(_SKILL_DEFINITIONS.values())
