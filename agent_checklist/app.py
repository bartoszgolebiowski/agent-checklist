from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from agent_checklist.domain import Decision, DecisionType
from agent_checklist.engine import Coordinator, Executor
from agent_checklist.memory import state_manager
from agent_checklist.memory.models import ResearchState
from agent_checklist.services.persistence import (
    ChecklistRepository,
    ChecklistStorageConfig,
)


@dataclass(frozen=True, slots=True)
class ChecklistAgent:
    """High-level façade that glues together the coordinator, executor, and memory."""

    coordinator: Coordinator
    executor: Executor
    repository: ChecklistRepository
    state: ResearchState = field(default_factory=state_manager.create_initial_state)

    def ingest_description(self, description: str) -> None:
        self._swap_state(state_manager.ingest_user_description(self.state, description))

    def record_refinement_feedback(self, feedback: str) -> None:
        self._swap_state(state_manager.record_user_feedback(self.state, feedback))

    def approve_checklist(self) -> None:
        self._swap_state(state_manager.mark_checklist_approved(self.state))

    def request_more_changes(self, reason: str) -> None:
        self._swap_state(state_manager.mark_checklist_rejected(self.state, reason))

    def start_tracking(self) -> None:
        self._swap_state(state_manager.activate_tracking_mode(self.state))

    def ingest_progress_update(self, update: str) -> None:
        self._swap_state(state_manager.ingest_progress_input(self.state, update))

    def acknowledge_progress(self) -> None:
        self._swap_state(state_manager.acknowledge_progress_ack(self.state))

    def acknowledge_summary(self) -> None:
        self._swap_state(state_manager.acknowledge_summary_delivery(self.state))

    def save_checklist(self) -> Path:
        artifact = state_manager.build_artifact(self.state)
        file_path = self.repository.save(artifact)
        self._swap_state(
            state_manager.record_save_result(self.state, artifact, str(file_path))
        )
        self._swap_state(state_manager.activate_tracking_mode(self.state))
        return file_path

    def next_decision(self) -> Decision:
        return self.coordinator.next_action(self.state)

    def run_planned_action(
        self, *, context: Mapping[str, object] | None = None
    ) -> Decision:
        decision = self.next_decision()
        if (
            decision.decision_type == DecisionType.LLM_SKILL
            and decision.skill is not None
        ):
            output = self.executor.run_skill(
                skill_name=decision.skill,
                state=self.state,
                context=context or decision.metadata or None,
            )
            self._swap_state(
                state_manager.update_state_from_skill(
                    self.state, decision.skill, output
                )
            )
        return decision

    @property
    def phase(self) -> str:
        return self.state.workflow.phase.value

    @classmethod
    def from_env(
        cls,
        *,
        executor: Executor | None = None,
        state: ResearchState | None = None,
    ) -> ChecklistAgent:
        """Factory that wires defaults using environment variables."""

        config = ChecklistStorageConfig.from_env()
        repository = ChecklistRepository(config=config)
        runtime_executor = executor
        if runtime_executor is None:
            from agent_checklist.llm.client import LLMClient, LLMConfig

            runtime_executor = Executor(client=LLMClient(config=LLMConfig.from_env()))

        coordinator = Coordinator()
        return cls(
            coordinator=coordinator,
            executor=runtime_executor,
            repository=repository,
            state=state or state_manager.create_initial_state(),
        )

    def _swap_state(self, new_state: ResearchState) -> None:
        object.__setattr__(self, "state", new_state)
