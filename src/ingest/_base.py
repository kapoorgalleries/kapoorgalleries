"""Abstract base class for ingesters.

Every ingester takes a path or Drive file id and yields:
  - one SourceRecord describing the source itself
  - many Observation rows
  - optionally many WorkImage rows

Ingesters never write to the DB directly; the CLI is responsible for
persistence. This keeps each ingester pure and testable.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Iterator

from ..schema import Observation, SourceRecord, WorkImage


@dataclasses.dataclass
class IngestResult:
    source: SourceRecord
    observations: list[Observation]
    images: list[WorkImage] = dataclasses.field(default_factory=list)


class Ingester:
    """Subclasses implement ``run()`` to return a fully-materialized IngestResult."""

    type: str = "unknown"

    def __init__(self, file_path: Path | str, drive_file_id: str | None = None):
        self.file_path = Path(file_path)
        self.drive_file_id = drive_file_id

    def run(self) -> IngestResult:
        raise NotImplementedError

    def _make_source(self, name: str | None = None, **kwargs) -> SourceRecord:
        from datetime import datetime, timezone
        return SourceRecord(
            name=name or self.file_path.name,
            type=self.type,
            drive_file_id=self.drive_file_id,
            drive_file_path=str(self.file_path),
            file_modified_at=datetime.fromtimestamp(
                self.file_path.stat().st_mtime, tz=timezone.utc
            ).isoformat() if self.file_path.exists() else None,
            **kwargs,
        )
