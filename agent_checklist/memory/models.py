from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from agent_checklist.domain import (
    ChecklistItemStatus,
    ConversationEntryKind,
    WorkflowPhase,
)


class ChecklistSubItem(BaseModel):
    """Represents a nested sub-checklist entry for a parent item."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    sub_item_id: str
    summary: str
    detail: str | None = None
    status: ChecklistItemStatus = ChecklistItemStatus.PENDING
    success_criteria: str | None = None
    notes: list[str] = Field(default_factory=list)


class ChecklistItem(BaseModel):
    """Represents a single actionable checklist entry with nested subtasks."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    item_id: str
    summary: str
    detail: str | None = None
    status: ChecklistItemStatus = ChecklistItemStatus.PENDING
    success_criteria: str | None = None
    notes: list[str] = Field(default_factory=list)
    sub_items: list[ChecklistSubItem] = Field(default_factory=list)


class RefinementPrompt(BaseModel):
    """Represents a follow-up question awaiting the user's response."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    question: str
    intent: str


class RefinementExchange(BaseModel):
    """Stores a clarification question and the corresponding user answer."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    question: str
    answer: str
    intent: str
    collected_at: datetime = Field(default_factory=datetime.utcnow)


class ConversationEntry(BaseModel):
    """Canonical representation of a conversational turn."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    entry_id: str = Field(default_factory=lambda: uuid4().hex)
    kind: ConversationEntryKind
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProgressLogEntry(BaseModel):
    """Captures how the user described progress against the checklist."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    entry_id: str = Field(default_factory=lambda: uuid4().hex)
    user_text: str
    referenced_item_ids: list[str] = Field(default_factory=list)
    status_transitions: dict[str, ChecklistItemStatus] = Field(default_factory=dict)
    sub_status_transitions: dict[str, ChecklistItemStatus] = Field(default_factory=dict)
    contextual_notes: str | None = None
    recorded_at: datetime = Field(default_factory=datetime.utcnow)


class CoreMemory(BaseModel):
    """Fixed identity and persona of the agent."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    persona_name: str = "AI Checklist Agent"
    mission: str = (
        "Transform user goals into measurable checklists, guide execution through "
        "dialogue, and summarize outcomes with documented context."
    )
    version: str = "1.0.0"


class SemanticMemory(BaseModel):
    """User-specific preferences or historical knowledge."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    user_handle: str | None = None
    preferred_tone: str = "collaborative"
    timezone: str | None = None
    saved_preferences: dict[str, Any] = Field(default_factory=dict)


class WorkflowState(BaseModel):
    """Tracks deterministic workflow flags for the state machine."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    phase: WorkflowPhase = WorkflowPhase.IDLE
    questions_asked: int = 0
    max_refinement_questions: int = 3
    checklist_finalized: bool = False
    pending_save: bool = False
    listening_started_at: datetime | None = None
    last_transition_at: datetime = Field(default_factory=datetime.utcnow)
    awaiting_clarification: bool = False


class WorkingMemory(BaseModel):
    """Holds the mutable conversation artifacts for the active checklist."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    original_description: str | None = None
    checklist_items: list[ChecklistItem] = Field(default_factory=list)
    refinement_questions: list[RefinementPrompt] = Field(default_factory=list)
    refinement_exchanges: list[RefinementExchange] = Field(default_factory=list)
    latest_user_message: str | None = None
    conversation_log: list[ConversationEntry] = Field(default_factory=list)
    progress_log: list[ProgressLogEntry] = Field(default_factory=list)
    checklist_file_path: str | None = None
    completion_summary: str | None = None
    clarification_prompt: str | None = None


class ResearchState(BaseModel):
    """Aggregate memory tree consumed by the coordinator."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    core: CoreMemory = Field(default_factory=CoreMemory)
    semantic: SemanticMemory = Field(default_factory=SemanticMemory)
    workflow: WorkflowState = Field(default_factory=WorkflowState)
    working: WorkingMemory = Field(default_factory=WorkingMemory)


class ChecklistArtifactItem(BaseModel):
    """Serializable representation stored on disk."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    summary: str
    detail: str | None = None
    status: ChecklistItemStatus
    notes: list[str] = Field(default_factory=list)
    sub_items: list[ChecklistSubItem] = Field(default_factory=list)


class ChecklistArtifact(BaseModel):
    """Snapshot persisted when the checklist is finalized."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    task_description: str
    created_at: datetime
    items: list[ChecklistArtifactItem]
    refinement_context: list[RefinementExchange]
    progress_log: list[ProgressLogEntry]
    completion_notes: str | None = None
    conversation_excerpt: list[ConversationEntry] = Field(default_factory=list)
