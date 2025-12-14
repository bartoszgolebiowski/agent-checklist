from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from agent_checklist.memory.models import ChecklistArtifact


@dataclass(frozen=True, slots=True)
class ChecklistStorageConfig:
    """Filesystem configuration for checklist persistence."""

    base_path: Path

    @classmethod
    def from_env(cls) -> ChecklistStorageConfig:
        root = Path(os.getenv("CHECKLIST_STORAGE_DIR", "storage/checklists"))
        return cls(base_path=root)


@dataclass(frozen=True, slots=True)
class ChecklistRepository:
    """Handles serialization of checklist artifacts."""

    config: ChecklistStorageConfig

    def save(self, artifact: ChecklistArtifact) -> Path:
        target_dir = self.config.base_path
        target_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        file_path = target_dir / f"checklist_{timestamp}.json"
        with file_path.open("w", encoding="utf-8") as fp:
            json.dump(artifact.model_dump(mode="json"), fp, indent=2)
        return file_path

    def load(self, path: Path) -> ChecklistArtifact:
        with path.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
        return ChecklistArtifact.model_validate(data)
