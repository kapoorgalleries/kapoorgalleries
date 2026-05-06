"""Index a directory of KG-####.png images.

For each file matching ``KG-\\d+\\.(png|jpe?g|webp)``, record bytes and flag
files smaller than 1 KB as placeholders (the Artsy First-100 PNG folder is
full of 75-byte 1×1 placeholder PNGs).
"""

from __future__ import annotations

import re
from pathlib import Path

from ..ids import parse_kg_id
from ..schema import Observation, WorkImage
from ._base import IngestResult, Ingester

EXT_RE = re.compile(r"\.(png|jpe?g|webp|tiff?)$", re.IGNORECASE)
PLACEHOLDER_BYTES = 1024


class ImageDirIngester(Ingester):
    type = "image_dir"

    def run(self) -> IngestResult:
        observations: list[Observation] = []
        images: list[WorkImage] = []
        n_files = 0
        if self.file_path.exists():
            for p in sorted(self.file_path.iterdir()):
                if not EXT_RE.search(p.name):
                    continue
                n_files += 1
                kg = parse_kg_id(p.stem)
                if not kg:
                    continue
                size = p.stat().st_size
                images.append(WorkImage(
                    work_id=kg,
                    drive_file_id=None,
                    bytes=size,
                    is_placeholder=size < PLACEHOLDER_BYTES,
                ))
                if size < PLACEHOLDER_BYTES:
                    observations.append(Observation(
                        work_id=kg,
                        field="primary_image_url",
                        value=None,  # placeholder; consolidator ignores empty
                        source_row_ref=str(p.name),
                        confidence="low",
                    ))
        return IngestResult(
            source=self._make_source(row_count=n_files),
            observations=observations,
            images=images,
        )
