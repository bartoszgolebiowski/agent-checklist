from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from agent_checklist.domain import ChecklistItemStatus


class ChecklistSubBullet(BaseModel):
    """Structure for a nested sub-task proposal."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    summary: str
    detail: str | None = None
    success_criteria: str | None = None


class ChecklistBullet(BaseModel):
    """Structure for a single checklist proposal from the LLM."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    summary: str
    detail: str | None = None
    success_criteria: str | None = None
    sub_items: list[ChecklistSubBullet] = Field(default_factory=list)


class GenerateInitialChecklistOutput(BaseModel):
    """Output for the initial checklist creation skill."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    ai_response: str
    items: list[ChecklistBullet] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class RefinementQuestionModel(BaseModel):
    """Represents a single follow-up question for the user."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    question: str
    intent: str
    missing_detail: str | None = None


class GenerateRefinementQuestionsOutput(BaseModel):
    """Structured output that contains up to three targeted questions."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    ai_response: str
    questions: list[RefinementQuestionModel] = Field(default_factory=list)


class RefinementUpdateModel(BaseModel):
    """Describes how the checklist should be modified after refinement."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    item_id: str | None = None
    action: Literal["add", "update", "remove"]
    summary: str | None = None
    detail: str | None = None
    success_criteria: str | None = None
    sub_items: list[ChecklistSubBullet] = Field(default_factory=list)
    sub_item_updates: list["RefinementSubItemUpdateModel"] = Field(default_factory=list)


class RefinementSubItemUpdateModel(BaseModel):
    """Describes how nested sub-items should change."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    sub_item_id: str | None = None
    action: Literal["add", "update", "remove"]
    summary: str | None = None
    detail: str | None = None
    success_criteria: str | None = None


class IncorporateRefinementsOutput(BaseModel):
    """Output of the skill that merges user feedback into the checklist."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    ai_response: str
    updates: list[RefinementUpdateModel] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ProgressSignalModel(BaseModel):
    """Represents progress inferred from conversational input."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    item_ids: list[str] = Field(default_factory=list)
    sub_item_ids: list[str] = Field(default_factory=list)
    new_status: ChecklistItemStatus | None = None
    note: str | None = None
    context: str | None = None


class InterpretProgressUpdateOutput(BaseModel):
    """Skill output for interpreting user updates during tracking."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    ai_response: str
    signals: list[ProgressSignalModel] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_prompt: str | None = None


class CompletionSummaryOutput(BaseModel):
    """Structured completion summary after all items are done."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    ai_response: str
    accomplishments: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    timeline: list[str] = Field(default_factory=list)
