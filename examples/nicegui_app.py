from __future__ import annotations

import json

from dotenv import load_dotenv
from nicegui import ui

from agent_checklist import ChecklistAgent
from agent_checklist.domain import (
    ChecklistItemStatus,
    ConversationEntryKind,
    DecisionType,
    WorkflowPhase,
)

load_dotenv()
agent = ChecklistAgent.from_env()
_rendered_entry_ids: set[str] = set()

change_dialog = None
change_reason = None
chat_container = None
message_box = None
phase_label = None
state_view = None
checklist_container = None


def append_chat(name: str, text: str, *, me: bool = False) -> None:
    if chat_container is None:
        return
    with chat_container:
        ui.chat_message(text=text, name=name, sent=me)
    chat_container.scroll_to(percent=100)


def refresh_state() -> None:
    if phase_label is None or state_view is None:
        return
    phase_label.text = f"Phase: {agent.phase}"
    state_snapshot = agent.state.model_dump(mode="json")
    state_view.set_content(json.dumps(state_snapshot, indent=2))
    refresh_checklist()


def refresh_checklist() -> None:
    if checklist_container is None:
        return
    checklist_container.clear()
    with checklist_container:
        items = agent.state.working.checklist_items
        if not items:
            ui.label("No checklist items yet.")
            return
        icon_map = {
            ChecklistItemStatus.PENDING: "☐",
            ChecklistItemStatus.IN_PROGRESS: "⏳",
            ChecklistItemStatus.COMPLETE: "☑",
        }
        for item in items:
            status_icon = icon_map.get(item.status, "☐")
            ui.label(f"{status_icon} {item.summary}")
            if item.sub_items:
                for sub in item.sub_items:
                    sub_status_icon = icon_map.get(sub.status, "☐")
                    ui.label(f"  {sub_status_icon} {sub.summary}").classes(
                        "text-sm ml-4"
                    )


def sync_chat_log() -> None:
    for entry in agent.state.working.conversation_log:
        if entry.entry_id in _rendered_entry_ids:
            continue
        if entry.kind == ConversationEntryKind.AGENT:
            append_chat("Agent", entry.content)
        elif entry.kind == ConversationEntryKind.SYSTEM:
            append_chat("System", entry.content)
        _rendered_entry_ids.add(entry.entry_id)


def run_llm_loop() -> None:
    while True:
        decision = agent.run_planned_action()
        if decision.decision_type != DecisionType.LLM_SKILL:
            break
    sync_chat_log()
    refresh_state()


def handle_user_message() -> None:
    if message_box is None:
        return
    text = (message_box.value or "").strip()
    if not text:
        return
    message_box.value = ""
    append_chat("You", text, me=True)
    if text.startswith("/") and handle_command(text):
        sync_chat_log()
        refresh_state()
        return
    route_freeform_message(text)
    sync_chat_log()
    refresh_state()


def handle_command(command: str) -> bool:
    cmd, *rest = command.split(maxsplit=1)
    payload = rest[0].strip() if rest else ""
    if cmd == "/approve":
        approve_action()
        return True
    if cmd == "/revise":
        if not payload:
            ui.notify("Provide a reason after /revise", color="warning")
            return False
        request_changes(payload)
        return True
    if cmd == "/save":
        save_action()
        return True
    if cmd == "/ack":
        acknowledge_progress_action()
        return True
    if cmd == "/summary":
        acknowledge_summary_action()
        return True
    ui.notify("Unknown command", color="negative")
    return False


def route_freeform_message(text: str) -> None:
    phase = agent.state.workflow.phase
    if phase == WorkflowPhase.IDLE:
        agent.ingest_description(text)
        run_llm_loop()
        return
    if phase in {
        WorkflowPhase.ASKING_REFINEMENT_QUESTIONS,
        WorkflowPhase.AWAITING_USER_RESPONSE,
        WorkflowPhase.PROCESSING_FEEDBACK,
    }:
        agent.record_refinement_feedback(text)
        run_llm_loop()
        return
    if phase in {
        WorkflowPhase.LISTENING_FOR_PROGRESS,
        WorkflowPhase.RECEIVING_USER_INPUT,
        WorkflowPhase.INTERPRETING_INTENT,
        WorkflowPhase.LOGGING_CONTEXT,
        WorkflowPhase.ASKING_CLARIFICATION,
        WorkflowPhase.ACKNOWLEDGING_PROGRESS,
    }:
        agent.ingest_progress_update(text)
        run_llm_loop()
        return
    ui.notify(
        "This phase expects a command (e.g., /approve or /save).", color="warning"
    )


def show_change_dialog() -> None:
    if change_dialog is None or change_reason is None:
        ui.notify("Change dialog not ready", color="warning")
        return
    change_reason.value = ""
    change_dialog.open()


def submit_request_changes() -> None:
    if change_reason is None:
        return
    request_changes(change_reason.value or "", close_dialog=True)


def request_changes(reason: str, *, close_dialog: bool = False) -> None:
    trimmed = reason.strip()
    if not trimmed:
        ui.notify("No change request submitted", color="warning")
        return
    agent.request_more_changes(trimmed)
    if close_dialog and change_dialog is not None:
        change_dialog.close()
    run_llm_loop()
    ui.notify("Change request recorded")


def approve_action() -> None:
    agent.approve_checklist()
    run_llm_loop()
    ui.notify("Checklist approved")


def save_action() -> None:
    path = agent.save_checklist()
    run_llm_loop()
    ui.notify(f"Checklist saved to {path}")


def acknowledge_progress_action() -> None:
    agent.acknowledge_progress()
    refresh_state()
    ui.notify("Progress acknowledged")


def acknowledge_summary_action() -> None:
    agent.acknowledge_summary()
    refresh_state()
    ui.notify("Summary acknowledged")


with ui.row().classes("w-full gap-4 p-4"):
    with ui.card().classes("w-1/3 flex flex-col gap-2"):
        ui.label("Checklist Agent Chat")
        with ui.expansion("Commands", icon="info", value=False):
            ui.markdown(
                """
                - `/approve` – approve the current checklist
                - `/revise <reason>` – request more changes
                - `/save` – persist the checklist (enabled after approval)
                - `/ack` – acknowledge progress prompt to continue listening
                - `/summary` – acknowledge the final summary
                """
            )
        chat_container = ui.scroll_area().classes("gap-2").style("max-height: 60vh;")
        with ui.row().classes("w-full gap-2"):
            message_box = ui.input(
                placeholder="Type a description, answer, or progress update..."
            ).classes("grow")
            ui.button("Send", on_click=handle_user_message)
        with ui.row().classes("gap-2"):
            ui.button("Approve Checklist", on_click=approve_action, color="positive")
            ui.button("Request Changes", on_click=show_change_dialog)
            ui.button("Save Checklist", on_click=save_action)
            ui.button("Acknowledge Summary", on_click=acknowledge_summary_action)
        with ui.row().classes("gap-2"):
            ui.button("Acknowledge Progress", on_click=acknowledge_progress_action)
    with ui.card().classes("w-1/3 flex flex-col gap-2"):
        ui.label("Checklist Display")
        checklist_container = ui.scroll_area().style("max-height: 70vh;")
    with ui.card().classes("w-1/3 flex flex-col gap-2"):
        ui.label("Memory Inspector")
        phase_label = ui.label(f"Phase: {agent.phase}")
        state_view = ui.code("{}", language="json").style(
            "max-height: 70vh; overflow-y: auto;"
        )
        ui.button("Refresh Memory", on_click=refresh_state)


with ui.dialog() as change_dialog, ui.card().classes("min-w-[20rem] gap-2"):
    ui.label("Request Checklist Changes")
    change_reason = ui.textarea(placeholder="Describe what needs to change...").props(
        "autogrow"
    )
    with ui.row().classes("justify-end gap-2"):
        ui.button("Cancel", on_click=change_dialog.close)
        ui.button("Submit", on_click=submit_request_changes)


sync_chat_log()
refresh_state()

ui.run(title="AI Checklist Agent Console")
