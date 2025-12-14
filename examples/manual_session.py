from __future__ import annotations

from typing import Iterable

from dotenv import load_dotenv

from agent_checklist import ChecklistAgent
from agent_checklist.domain import (
    ChecklistItemStatus,
    ConversationEntryKind,
    WorkflowPhase,
)


def main() -> None:
    load_dotenv()
    agent = ChecklistAgent.from_env()
    print("AI Checklist Agent manual session. Press Ctrl+C to exit.\n")
    description = _capture_block("Describe the objective you want to tackle:")
    if not description:
        print("No description provided. Exiting.")
        return

    agent.ingest_description(description)
    agent.run_planned_action()
    _print_latest_agent_turn(agent, limit=3)
    _print_checklist(agent)

    if not _run_refinement_dialog(agent):
        print("Checklist was not approved. Exiting without persistence.")
        return

    path = agent.save_checklist()
    print(f"Checklist snapshot saved to {path}")
    print("Tracking mode: you can log progress updates to keep the agent in sync.\n")
    _tracking_loop(agent)
    print("Session complete.")


def _run_refinement_dialog(agent: ChecklistAgent) -> bool:
    while True:
        phase = agent.state.workflow.phase
        if phase == WorkflowPhase.ASKING_REFINEMENT_QUESTIONS:
            agent.run_planned_action()
            if agent.state.working.refinement_questions:
                _print_refinement_questions(agent)
                answer = _capture_block(
                    "Respond to the agent's questions (blank line to skip):"
                )
                if answer:
                    agent.record_refinement_feedback(answer)
                else:
                    print(
                        "No response captured. You can approve or request more changes."
                    )
            continue

        if phase == WorkflowPhase.AWAITING_USER_RESPONSE:
            answer = _capture_block("Provide your clarification:")
            if answer:
                agent.record_refinement_feedback(answer)
            else:
                print("No response captured.")
            continue

        if phase == WorkflowPhase.PROCESSING_FEEDBACK:
            agent.run_planned_action()
            _print_checklist(agent)
            continue

        if phase == WorkflowPhase.CHECK_APPROVAL:
            choice = (
                input("Approve checklist? [a]pprove/[r]efine/[q]uit: ").strip().lower()
            )
            if choice.startswith("a"):
                agent.approve_checklist()
                return True
            if choice.startswith("r"):
                reason = (
                    _capture_block("Describe what still needs to change:")
                    or "Please refine further."
                )
                agent.request_more_changes(reason)
                continue
            if choice.startswith("q"):
                return False
            print("Please choose a, r, or q.")
            continue

        if phase in {WorkflowPhase.SAVING_CHECKLIST, WorkflowPhase.CONFIRMING_SAVE}:
            return True

        return False


def _tracking_loop(agent: ChecklistAgent) -> None:
    while True:
        if agent.state.workflow.phase == WorkflowPhase.SESSION_COMPLETE:
            break
        choice = input("Log a progress update now? [y/N]: ").strip().lower()
        if choice != "y":
            break
        update = _capture_block("Describe recent progress:")
        if not update:
            print("No progress captured.")
            continue
        agent.ingest_progress_update(update)
        agent.run_planned_action()
        _print_latest_agent_turn(agent)
        if _handle_progress_followups(agent):
            break


def _handle_progress_followups(agent: ChecklistAgent) -> bool:
    while agent.state.workflow.phase == WorkflowPhase.ASKING_CLARIFICATION:
        prompt = (
            agent.state.working.clarification_prompt
            or "Please clarify your previous update."
        )
        clarification = _capture_block(prompt)
        if not clarification:
            print("No clarification supplied; returning to listening mode.")
            agent.acknowledge_progress()
            return False
        agent.ingest_progress_update(clarification)
        agent.run_planned_action()
        _print_latest_agent_turn(agent)

    if agent.state.workflow.phase == WorkflowPhase.GENERATING_SUMMARY:
        agent.run_planned_action()
        _print_latest_agent_turn(agent, limit=2)
        agent.acknowledge_summary()
        return True

    if agent.state.workflow.phase == WorkflowPhase.PRESENTING_SUMMARY:
        _print_latest_agent_turn(agent, limit=2)
        agent.acknowledge_summary()
        return True

    if agent.state.workflow.phase == WorkflowPhase.ACKNOWLEDGING_PROGRESS:
        agent.acknowledge_progress()
        return False

    if agent.state.workflow.phase == WorkflowPhase.SESSION_COMPLETE:
        return True

    return False


def _print_checklist(agent: ChecklistAgent) -> None:
    status_symbols = {
        ChecklistItemStatus.PENDING: " ",
        ChecklistItemStatus.IN_PROGRESS: "~",
        ChecklistItemStatus.COMPLETE: "x",
    }
    print("\nCurrent Checklist:")
    for item in agent.state.working.checklist_items:
        symbol = status_symbols.get(item.status, "?")
        detail = f" ({item.detail})" if item.detail else ""
        print(f" [{symbol}] {item.item_id}: {item.summary}{detail}")
        if item.success_criteria:
            print(f"        success: {item.success_criteria}")
        if item.notes:
            print(f"        notes: {'; '.join(item.notes)}")
        if item.sub_items:
            print("        sub-checklist:")
            for sub in item.sub_items:
                sub_symbol = status_symbols.get(sub.status, "?")
                sub_detail = f" ({sub.detail})" if sub.detail else ""
                print(
                    f"          [{sub_symbol}] {sub.sub_item_id}: {sub.summary}{sub_detail}"
                )
                if sub.success_criteria:
                    print(f"              success: {sub.success_criteria}")
                if sub.notes:
                    print(f"              notes: {'; '.join(sub.notes)}")
    print()


def _print_refinement_questions(agent: ChecklistAgent) -> None:
    print("\nAgent Clarification Questions:")
    for idx, prompt in enumerate(agent.state.working.refinement_questions, start=1):
        intent = f" (intent: {prompt.intent})" if prompt.intent else ""
        print(f" {idx}. {prompt.question}{intent}")
    print()


def _print_latest_agent_turn(agent: ChecklistAgent, *, limit: int = 1) -> None:
    entries = [
        entry
        for entry in agent.state.working.conversation_log
        if entry.kind == ConversationEntryKind.AGENT
    ]
    for entry in entries[-limit:]:
        print("Agent:\n------")
        print(entry.content.strip())
        if entry.metadata:
            print(f"meta: {entry.metadata}")
        print()


def _capture_block(prompt: str) -> str:
    print(prompt)
    print("Enter text. Submit an empty line to finish.")
    lines: list[str] = []
    try:
        while True:
            line = input("> ")
            if not line.strip():
                break
            lines.append(line)
    except KeyboardInterrupt:  # pragma: no cover - interactive input only
        print("\nKeyboard interrupt detected. Returning to menu.")
        return ""
    return "\n".join(lines).strip()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:  # pragma: no cover - interactive script
        print("\nSession aborted by user.")
