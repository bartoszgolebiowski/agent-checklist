from __future__ import annotations

from dataclasses import dataclass

from agent_checklist.domain import Decision, SkillName, WorkflowPhase
from agent_checklist.memory.models import ResearchState


@dataclass(frozen=True, slots=True)
class Coordinator:
    """Deterministic state machine that decides the next system action."""

    def next_action(self, state: ResearchState) -> Decision:
        phase = state.workflow.phase

        if phase == WorkflowPhase.GENERATING_CHECKLIST:
            return Decision.llm(
                skill=SkillName.GENERATE_INITIAL_CHECKLIST,
                reason="Transform the goal description into a checklist",
            )

        if phase == WorkflowPhase.ASKING_REFINEMENT_QUESTIONS:
            if (
                state.workflow.questions_asked
                >= state.workflow.max_refinement_questions
            ):
                return Decision.noop(
                    reason="Awaiting user responses because refinement question limit was reached",
                )
            return Decision.llm(
                skill=SkillName.GENERATE_REFINEMENT_QUESTIONS,
                reason="Need up to three clarifying questions",
            )

        if phase == WorkflowPhase.PROCESSING_FEEDBACK:
            return Decision.llm(
                skill=SkillName.INCORPORATE_REFINEMENTS,
                reason="User provided refinement feedback",
            )

        if phase == WorkflowPhase.INTERPRETING_INTENT:
            return Decision.llm(
                skill=SkillName.INTERPRET_PROGRESS_UPDATE,
                reason="Interpret the latest progress update",
            )

        if phase == WorkflowPhase.GENERATING_SUMMARY:
            return Decision.llm(
                skill=SkillName.GENERATE_COMPLETION_SUMMARY,
                reason="All items complete; compile the final summary",
            )

        return Decision.noop(reason="No LLM action required for the current phase")
