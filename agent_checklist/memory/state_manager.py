from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Callable, Mapping

from pydantic import BaseModel

from agent_checklist.domain import (
    MAX_REFINEMENT_QUESTIONS,
    ChecklistItemStatus,
    ConversationEntryKind,
    SkillName,
    WorkflowPhase,
)
from agent_checklist.memory.models import (
    ChecklistArtifact,
    ChecklistArtifactItem,
    ChecklistItem,
    ChecklistSubItem,
    ConversationEntry,
    ProgressLogEntry,
    RefinementExchange,
    RefinementPrompt,
    ResearchState,
)
from agent_checklist.skills import models as skill_models

SkillHandler = Callable[[ResearchState, BaseModel], ResearchState]


def _next_item_id(existing_ids: Mapping[str, ChecklistItem]) -> str:
    max_index = 0
    for item_id in existing_ids:
        if item_id.startswith("item-"):
            try:
                idx = int(item_id.split("-", 1)[1])
            except ValueError:
                continue
            max_index = max(max_index, idx)
    return f"item-{max_index + 1}"


def _next_sub_item_id(parent_id: str, existing_ids: set[str]) -> str:
    prefix = f"{parent_id}-"
    max_index = 0
    for sub_id in existing_ids:
        if sub_id.startswith(prefix):
            try:
                idx = int(sub_id.split("-")[-1])
            except ValueError:
                continue
            max_index = max(max_index, idx)
    return f"{parent_id}-{max_index + 1}"


def _build_sub_items_from_bullets(
    parent_id: str, sub_bullets: list[skill_models.ChecklistSubBullet]
) -> list[ChecklistSubItem]:
    return [
        ChecklistSubItem(
            sub_item_id=f"{parent_id}-{index + 1}",
            summary=sub.summary,
            detail=sub.detail,
            success_criteria=sub.success_criteria,
        )
        for index, sub in enumerate(sub_bullets)
    ]


def _apply_sub_item_updates(
    item: ChecklistItem, updates: list[skill_models.RefinementSubItemUpdateModel]
) -> None:
    if not updates:
        return

    sub_items = list(item.sub_items)
    sub_map = {sub.sub_item_id: sub for sub in sub_items}

    for change in updates:
        if change.action == "add":
            if not change.summary:
                continue
            new_id = change.sub_item_id or _next_sub_item_id(item.item_id, set(sub_map))
            new_sub = ChecklistSubItem(
                sub_item_id=new_id,
                summary=change.summary,
                detail=change.detail,
                success_criteria=change.success_criteria,
            )
            sub_items.append(new_sub)
            sub_map[new_id] = new_sub
        elif change.action == "remove" and change.sub_item_id in sub_map:
            sub_items = [
                sub for sub in sub_items if sub.sub_item_id != change.sub_item_id
            ]
            sub_map.pop(change.sub_item_id, None)
        elif change.action == "update" and change.sub_item_id in sub_map:
            sub = sub_map[change.sub_item_id]
            sub.summary = change.summary or sub.summary
            sub.detail = change.detail or sub.detail
            sub.success_criteria = change.success_criteria or sub.success_criteria

    item.sub_items = sub_items


def create_initial_state(*, user_handle: str | None = None) -> ResearchState:
    """Bootstraps the state tree with optional semantic defaults."""

    state = ResearchState()
    state.semantic.user_handle = user_handle
    state.workflow.max_refinement_questions = MAX_REFINEMENT_QUESTIONS
    return state


def ingest_user_description(state: ResearchState, description: str) -> ResearchState:
    """Captures the user's initial goal description and advances the phase."""

    new_state = deepcopy(state)
    sanitized = description.strip()
    if not sanitized:
        return new_state

    new_state.working.original_description = sanitized
    new_state.workflow.phase = WorkflowPhase.GENERATING_CHECKLIST
    new_state.workflow.last_transition_at = datetime.utcnow()
    new_state.working.conversation_log.append(
        ConversationEntry(kind=ConversationEntryKind.USER, content=sanitized)
    )
    return new_state


def record_user_feedback(state: ResearchState, feedback: str) -> ResearchState:
    """Stores user answers to refinement questions and queues checklist updates."""

    new_state = deepcopy(state)
    sanitized = feedback.strip()
    if not sanitized:
        return new_state

    new_state.working.latest_user_message = sanitized
    new_state.workflow.phase = WorkflowPhase.PROCESSING_FEEDBACK
    new_state.workflow.last_transition_at = datetime.utcnow()
    new_state.working.conversation_log.append(
        ConversationEntry(kind=ConversationEntryKind.USER, content=sanitized)
    )
    return new_state


def ingest_progress_input(state: ResearchState, user_message: str) -> ResearchState:
    """Records natural language progress updates before interpretation."""

    new_state = deepcopy(state)
    sanitized = user_message.strip()
    if not sanitized:
        return new_state

    new_state.working.latest_user_message = sanitized
    new_state.workflow.phase = WorkflowPhase.INTERPRETING_INTENT
    new_state.workflow.last_transition_at = datetime.utcnow()
    new_state.working.conversation_log.append(
        ConversationEntry(kind=ConversationEntryKind.USER, content=sanitized)
    )
    return new_state


def mark_checklist_approved(state: ResearchState) -> ResearchState:
    """Flags the checklist as finalized and ready for persistence."""

    new_state = deepcopy(state)
    new_state.workflow.checklist_finalized = True
    new_state.workflow.phase = WorkflowPhase.SAVING_CHECKLIST
    new_state.workflow.pending_save = True
    new_state.workflow.last_transition_at = datetime.utcnow()
    return new_state


def mark_checklist_rejected(state: ResearchState, reason: str) -> ResearchState:
    """Sends the workflow back to refinement with additional user guidance."""

    new_state = deepcopy(state)
    sanitized = reason.strip()
    if sanitized:
        new_state.working.conversation_log.append(
            ConversationEntry(kind=ConversationEntryKind.USER, content=sanitized)
        )
    new_state.workflow.phase = WorkflowPhase.PROCESSING_FEEDBACK
    new_state.workflow.last_transition_at = datetime.utcnow()
    return new_state


def record_save_result(
    state: ResearchState, artifact: ChecklistArtifact, file_path: str
) -> ResearchState:
    """Updates the working memory once the checklist snapshot has been written."""

    new_state = deepcopy(state)
    new_state.working.checklist_file_path = file_path
    new_state.workflow.pending_save = False
    new_state.workflow.phase = WorkflowPhase.CONFIRMING_SAVE
    new_state.workflow.last_transition_at = datetime.utcnow()
    new_state.working.conversation_log.append(
        ConversationEntry(
            kind=ConversationEntryKind.SYSTEM,
            content=f"Checklist saved to {file_path}",
            metadata={"artifact_summary": artifact.model_dump()},
        )
    )
    return new_state


def activate_tracking_mode(state: ResearchState) -> ResearchState:
    """Moves the workflow into the listening loop for progress updates."""

    new_state = deepcopy(state)
    new_state.workflow.phase = WorkflowPhase.LISTENING_FOR_PROGRESS
    new_state.workflow.listening_started_at = (
        new_state.workflow.listening_started_at or datetime.utcnow()
    )
    new_state.workflow.last_transition_at = datetime.utcnow()
    return new_state


def acknowledge_progress_ack(state: ResearchState) -> ResearchState:
    """Returns the workflow to the listening state after acknowledging progress."""

    new_state = deepcopy(state)
    new_state.workflow.phase = WorkflowPhase.LISTENING_FOR_PROGRESS
    new_state.workflow.awaiting_clarification = False
    new_state.workflow.last_transition_at = datetime.utcnow()
    new_state.working.clarification_prompt = None
    new_state.working.latest_user_message = None
    return new_state


def acknowledge_summary_delivery(state: ResearchState) -> ResearchState:
    """Completes the session once the completion summary has been shared."""

    new_state = deepcopy(state)
    new_state.workflow.phase = WorkflowPhase.SESSION_COMPLETE
    new_state.workflow.last_transition_at = datetime.utcnow()
    return new_state


def checklist_is_complete(state: ResearchState) -> bool:
    """Checks whether every checklist item has been marked complete."""

    if not state.working.checklist_items:
        return False

    for item in state.working.checklist_items:
        if item.status != ChecklistItemStatus.COMPLETE:
            return False
        if any(sub.status != ChecklistItemStatus.COMPLETE for sub in item.sub_items):
            return False
    return True


def update_state_from_skill(
    state: ResearchState, skill_name: SkillName, output: BaseModel
) -> ResearchState:
    """Dispatches structured LLM output to the corresponding handler."""

    handler = _SKILL_HANDLERS.get(skill_name)
    if handler is None:
        raise ValueError(f"No handler registered for skill: {skill_name}")
    return handler(state, output)


def build_artifact(state: ResearchState) -> ChecklistArtifact:
    """Creates a serializable artifact from the current state."""

    if state.working.original_description is None:
        raise ValueError("Cannot persist checklist without an original description")

    items = [
        ChecklistArtifactItem(
            summary=item.summary,
            detail=item.detail,
            status=item.status,
            notes=item.notes,
            sub_items=[
                ChecklistSubItem(
                    sub_item_id=sub.sub_item_id,
                    summary=sub.summary,
                    detail=sub.detail,
                    status=sub.status,
                    success_criteria=sub.success_criteria,
                    notes=sub.notes,
                )
                for sub in item.sub_items
            ],
        )
        for item in state.working.checklist_items
    ]
    return ChecklistArtifact(
        task_description=state.working.original_description,
        created_at=datetime.utcnow(),
        items=items,
        refinement_context=state.working.refinement_exchanges,
        progress_log=state.working.progress_log,
        completion_notes=state.working.completion_summary,
        conversation_excerpt=state.working.conversation_log[-10:],
    )


def _handle_generate_initial_checklist(
    state: ResearchState, output: skill_models.GenerateInitialChecklistOutput
) -> ResearchState:
    new_state = deepcopy(state)
    items: list[ChecklistItem] = []
    for index, bullet in enumerate(output.items):
        parent_id = f"item-{index + 1}"
        sub_items = _build_sub_items_from_bullets(parent_id, bullet.sub_items)
        items.append(
            ChecklistItem(
                item_id=parent_id,
                summary=bullet.summary,
                detail=bullet.detail,
                success_criteria=bullet.success_criteria,
                sub_items=sub_items,
            )
        )
    new_state.working.checklist_items = items
    new_state.workflow.questions_asked = 0
    new_state.workflow.phase = WorkflowPhase.ASKING_REFINEMENT_QUESTIONS
    new_state.workflow.last_transition_at = datetime.utcnow()
    new_state.working.conversation_log.append(
        ConversationEntry(
            kind=ConversationEntryKind.AGENT,
            content=output.ai_response,
            metadata={"skill": SkillName.GENERATE_INITIAL_CHECKLIST.value},
        )
    )
    return new_state


def _handle_generate_refinement_questions(
    state: ResearchState, output: skill_models.GenerateRefinementQuestionsOutput
) -> ResearchState:
    new_state = deepcopy(state)
    prompts = [
        RefinementPrompt(question=question.question, intent=question.intent)
        for question in output.questions
    ]
    new_state.working.refinement_questions = prompts
    new_state.workflow.questions_asked += len(prompts)
    new_state.workflow.phase = (
        WorkflowPhase.AWAITING_USER_RESPONSE
        if prompts
        else WorkflowPhase.CHECK_APPROVAL
    )
    new_state.workflow.last_transition_at = datetime.utcnow()
    agent_message = output.ai_response or "Here are a few clarification questions."
    new_state.working.conversation_log.append(
        ConversationEntry(
            kind=ConversationEntryKind.AGENT,
            content=agent_message,
            metadata={"skill": SkillName.GENERATE_REFINEMENT_QUESTIONS.value},
        )
    )
    for prompt in prompts:
        new_state.working.conversation_log.append(
            ConversationEntry(kind=ConversationEntryKind.AGENT, content=prompt.question)
        )
    return new_state


def _handle_incorporate_refinements(
    state: ResearchState, output: skill_models.IncorporateRefinementsOutput
) -> ResearchState:
    new_state = deepcopy(state)
    items_by_id: dict[str, ChecklistItem] = {
        item.item_id: item for item in new_state.working.checklist_items
    }

    for update in output.updates:
        if update.action == "add":
            if not update.summary:
                continue
            new_id = update.item_id or _next_item_id(items_by_id)
            new_item = ChecklistItem(
                item_id=new_id,
                summary=update.summary,
                detail=update.detail,
                success_criteria=update.success_criteria,
                sub_items=_build_sub_items_from_bullets(new_id, update.sub_items),
            )
            if update.sub_item_updates:
                _apply_sub_item_updates(new_item, update.sub_item_updates)
            new_state.working.checklist_items.append(new_item)
            items_by_id[new_id] = new_item
        elif (
            update.action == "remove"
            and update.item_id
            and update.item_id in items_by_id
        ):
            new_state.working.checklist_items = [
                item
                for item in new_state.working.checklist_items
                if item.item_id != update.item_id
            ]
            items_by_id.pop(update.item_id, None)
        elif (
            update.action == "update"
            and update.item_id
            and update.item_id in items_by_id
        ):
            item = items_by_id[update.item_id]
            item.summary = update.summary or item.summary
            item.detail = update.detail or item.detail
            item.success_criteria = update.success_criteria or item.success_criteria
            if update.sub_items:
                item.sub_items = _build_sub_items_from_bullets(
                    item.item_id, update.sub_items
                )
            _apply_sub_item_updates(item, update.sub_item_updates)

    answer_text = new_state.working.latest_user_message or ""
    for prompt in new_state.working.refinement_questions:
        new_state.working.refinement_exchanges.append(
            RefinementExchange(
                question=prompt.question, intent=prompt.intent, answer=answer_text
            )
        )

    new_state.working.refinement_questions = []
    new_state.working.latest_user_message = None
    new_state.workflow.phase = WorkflowPhase.CHECK_APPROVAL
    new_state.workflow.last_transition_at = datetime.utcnow()
    new_state.working.conversation_log.append(
        ConversationEntry(
            kind=ConversationEntryKind.AGENT,
            content=output.ai_response,
            metadata={"skill": SkillName.INCORPORATE_REFINEMENTS.value},
        )
    )
    return new_state


def _handle_interpret_progress_update(
    state: ResearchState, output: skill_models.InterpretProgressUpdateOutput
) -> ResearchState:
    new_state = deepcopy(state)
    items_by_id: dict[str, ChecklistItem] = {
        item.item_id: item for item in new_state.working.checklist_items
    }
    sub_items_by_id: dict[str, ChecklistSubItem] = {
        sub.sub_item_id: sub
        for item in new_state.working.checklist_items
        for sub in item.sub_items
    }

    for signal in output.signals:
        transition_map: dict[str, ChecklistItemStatus] = {}
        sub_transition_map: dict[str, ChecklistItemStatus] = {}
        for item_id in signal.item_ids:
            if item_id not in items_by_id:
                continue
            item = items_by_id[item_id]
            if signal.new_status and item.status != signal.new_status:
                item.status = signal.new_status
            if signal.note:
                item.notes.append(signal.note)
            transition_map[item_id] = item.status
        for sub_item_id in signal.sub_item_ids:
            sub_item = sub_items_by_id.get(sub_item_id)
            if not sub_item:
                continue
            if signal.new_status and sub_item.status != signal.new_status:
                sub_item.status = signal.new_status
            if signal.note:
                sub_item.notes.append(signal.note)
            sub_transition_map[sub_item_id] = sub_item.status
        if transition_map:
            new_state.working.progress_log.append(
                ProgressLogEntry(
                    user_text=new_state.working.latest_user_message or "",
                    referenced_item_ids=list(transition_map.keys()),
                    status_transitions=transition_map,
                    sub_status_transitions=sub_transition_map,
                    contextual_notes=signal.context,
                )
            )
        elif sub_transition_map:
            new_state.working.progress_log.append(
                ProgressLogEntry(
                    user_text=new_state.working.latest_user_message or "",
                    referenced_item_ids=[],
                    status_transitions={},
                    sub_status_transitions=sub_transition_map,
                    contextual_notes=signal.context,
                )
            )

    new_state.working.conversation_log.append(
        ConversationEntry(
            kind=ConversationEntryKind.AGENT,
            content=output.ai_response,
            metadata={"skill": SkillName.INTERPRET_PROGRESS_UPDATE.value},
        )
    )

    if output.needs_clarification:
        new_state.workflow.awaiting_clarification = True
        new_state.workflow.phase = WorkflowPhase.ASKING_CLARIFICATION
        new_state.working.clarification_prompt = output.clarification_prompt
    else:
        new_state.workflow.awaiting_clarification = False
        new_state.working.clarification_prompt = None
        new_state.workflow.phase = (
            WorkflowPhase.GENERATING_SUMMARY
            if checklist_is_complete(new_state)
            else WorkflowPhase.ACKNOWLEDGING_PROGRESS
        )

    new_state.workflow.last_transition_at = datetime.utcnow()
    return new_state


def _handle_completion_summary(
    state: ResearchState, output: skill_models.CompletionSummaryOutput
) -> ResearchState:
    new_state = deepcopy(state)
    new_state.working.completion_summary = output.ai_response
    new_state.workflow.phase = WorkflowPhase.PRESENTING_SUMMARY
    new_state.workflow.last_transition_at = datetime.utcnow()
    new_state.working.conversation_log.append(
        ConversationEntry(
            kind=ConversationEntryKind.AGENT,
            content=output.ai_response,
            metadata={"skill": SkillName.GENERATE_COMPLETION_SUMMARY.value},
        )
    )
    return new_state


_SKILL_HANDLERS: dict[SkillName, SkillHandler] = {
    SkillName.GENERATE_INITIAL_CHECKLIST: _handle_generate_initial_checklist,
    SkillName.GENERATE_REFINEMENT_QUESTIONS: _handle_generate_refinement_questions,
    SkillName.INCORPORATE_REFINEMENTS: _handle_incorporate_refinements,
    SkillName.INTERPRET_PROGRESS_UPDATE: _handle_interpret_progress_update,
    SkillName.GENERATE_COMPLETION_SUMMARY: _handle_completion_summary,
}
