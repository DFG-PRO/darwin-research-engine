"""Safe artifact storage for source content snapshots."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from darwin.content.errors import ArtifactStorageError


class ArtifactStore:
    """Write source content artifacts under a configured root."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def write_snapshot_artifact(
        self,
        *,
        research_run_id: uuid.UUID,
        source_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        filename: str,
        content: bytes,
    ) -> str:
        if filename not in {"raw.bin", "normalized.txt"}:
            raise ArtifactStorageError(f"Unsupported artifact filename: {filename}")

        relative_path = (
            Path("source-content")
            / str(research_run_id)
            / str(source_id)
            / str(snapshot_id)
            / filename
        )
        target_path = self._safe_path(relative_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        temporary_path = target_path.with_name(f".{target_path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temporary_path.open("xb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            temporary_path.replace(target_path)
        except OSError as exc:
            temporary_path.unlink(missing_ok=True)
            raise ArtifactStorageError(f"Artifact write failed: {exc.__class__.__name__}") from exc

        return relative_path.as_posix()

    def resolve_artifact_path(self, relative_path: str) -> Path:
        """Resolve an already stored relative artifact path safely."""

        return self._safe_path(Path(relative_path))

    def _safe_path(self, relative_path: Path) -> Path:
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ArtifactStorageError("Artifact path must stay inside artifact root")

        root = self.root.resolve()
        candidate = (root / relative_path).resolve()
        if root != candidate and root not in candidate.parents:
            raise ArtifactStorageError("Artifact path escaped artifact root")
        return candidate
