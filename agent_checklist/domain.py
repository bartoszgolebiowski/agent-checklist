from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, MutableMapping


class WorkflowPhase(str, Enum):
    """Enumerates every deterministic step in the checklist lifecycle."""

    IDLE = "idle"
    RECEIVING_DESCRIPTION = "receiving_description"
    GENERATING_CHECKLIST = "generating_checklist"
    PRESENTING_INITIAL_CHECKLIST = "presenting_initial_checklist"
    ASKING_REFINEMENT_QUESTIONS = "asking_refinement_questions"
    AWAITING_USER_RESPONSE = "awaiting_user_response"
    PROCESSING_FEEDBACK = "processing_feedback"
    UPDATING_CHECKLIST = "updating_checklist"
    PRESENTING_REVISED_CHECKLIST = "presenting_revised_checklist"
    CHECK_APPROVAL = "check_approval"
    SAVING_CHECKLIST = "saving_checklist"
    CONFIRMING_SAVE = "confirming_save"
    LISTENING_FOR_PROGRESS = "listening_for_progress"
    RECEIVING_USER_INPUT = "receiving_user_input"
    INTERPRETING_INTENT = "interpreting_intent"
    ASKING_CLARIFICATION = "asking_clarification"
    LOGGING_CONTEXT = "logging_context"
    PERSISTING_UPDATE = "persisting_update"
    ACKNOWLEDGING_PROGRESS = "acknowledging_progress"
    CHECKING_COMPLETION = "checking_completion"
    GENERATING_SUMMARY = "generating_summary"
    PRESENTING_SUMMARY = "presenting_summary"
    SESSION_COMPLETE = "session_complete"


class ChecklistItemStatus(str, Enum):
    """Lifecycle states for an individual checklist item."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


class ConversationEntryKind(str, Enum):
    """Categories of conversational logs captured by the agent."""

    SYSTEM = "system"
    USER = "user"
    AGENT = "agent"
    PROGRESS = "progress"


class SkillName(str, Enum):
    """Registered skill identifiers."""

    GENERATE_INITIAL_CHECKLIST = "generate_initial_checklist"
    GENERATE_REFINEMENT_QUESTIONS = "generate_refinement_questions"
    INCORPORATE_REFINEMENTS = "incorporate_refinements"
    INTERPRET_PROGRESS_UPDATE = "interpret_progress_update"
    GENERATE_COMPLETION_SUMMARY = "generate_completion_summary"


class DecisionType(str, Enum):
    """Control-flow directives produced by the coordinator."""

    LLM_SKILL = "llm_skill"
    TOOL = "tool"
    COMPLETE = "complete"
    NOOP = "noop"


SkillContext = Mapping[str, Any]
MutableSkillContext = MutableMapping[str, Any]

MAX_REFINEMENT_QUESTIONS = 3


@dataclass(frozen=True, slots=True)
class Decision:
    """Represents the next deterministic step for the agent runtime."""

    decision_type: DecisionType
    skill: SkillName | None = None
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def llm(cls, *, skill: SkillName, reason: str, metadata: Mapping[str, Any] | None = None) -> Decision:
        return cls(
            decision_type=DecisionType.LLM_SKILL,
            skill=skill,
            reason=reason,
            metadata=dict(metadata or {}),
        )

    @classmethod
    def tool(cls, *, tool: str, reason: str, metadata: Mapping[str, Any] | None = None) -> Decision:
        payload: dict[str, Any] = {"tool": tool}
        if metadata:
            payload.update(metadata)
        return cls(decision_type=DecisionType.TOOL, reason=reason, metadata=payload)

    @classmethod
    def complete(cls, *, reason: str) -> Decision:
        return cls(decision_type=DecisionType.COMPLETE, reason=reason)

    @classmethod
    def noop(cls, *, reason: str) -> Decision:
        return cls(decision_type=DecisionType.NOOP, reason=reason)
