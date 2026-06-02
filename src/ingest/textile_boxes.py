"""Ingester for the July 2022 Textile Boxes inventory.

Format: Word document with a "Box N: <topic>" hierarchy.  Items inside
a box don't have unique IDs (descriptions like "2 men's coats, early
20th C"), so the unit of identity is the BOX itself.  Each box becomes
one observation set:

    external_id        = 'Box-N'
    external_id_system = 'Textile Boxes 2022-07'
    title              = 'Box N: <topic>'
    provenance_text    = full text of the box contents

Searchable as a record without falsely separating un-IDed items.
"""

from __future__ import annotations

import re
import zipfile
from xml.etree import ElementTree as ET

from ..ids import unresolved_id
from ..schema import Observation
from ._base import IngestResult, Ingester

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
BOX_RE = re.compile(r"^\s*Box\s+(\d+)\s*[:\s]\s*(.*)$", re.IGNORECASE)


class TextileBoxesIngester(Ingester):
    type = "textile_boxes"

    def run(self) -> IngestResult:
        observations: list[Observation] = []
        if not self.file_path.exists():
            return IngestResult(
                source=self._make_source(row_count=0), observations=observations,
            )

        with zipfile.ZipFile(str(self.file_path)) as z:
            xml = z.read("word/document.xml").decode("utf-8")
        root = ET.fromstring(xml)
        paragraphs: list[str] = []
        for p in root.iter(W_NS + "p"):
            text = "".join(t.text or "" for t in p.iter(W_NS + "t"))
            text = text.strip()
            if text:
                paragraphs.append(text)

        # Group paragraphs by Box N: header.  Anything before the first
        # box header gets dropped.
        boxes: list[tuple[str, str, list[str]]] = []  # (num, topic, contents)
        current: tuple[str, str, list[str]] | None = None
        for line in paragraphs:
            m = BOX_RE.match(line)
            if m:
                if current:
                    boxes.append(current)
                current = (m.group(1), m.group(2).strip(), [])
            elif current:
                current[2].append(line)
        if current:
            boxes.append(current)

        collection = "Textile Boxes 2022-07"
        for num, topic, contents in boxes:
            extid = f"Box-{num}"
            title = f"Box {num}: {topic}" if topic else f"Box {num}"
            work_id = unresolved_id(collection, extid, title)
            ref = f"box={num}"
            observations.append(Observation(
                work_id=work_id, field="title", value=title,
                source_row_ref=ref, confidence="high",
            ))
            observations.append(Observation(
                work_id=work_id, field="external_id", value=extid,
                source_row_ref=ref, confidence="high",
            ))
            observations.append(Observation(
                work_id=work_id, field="external_id_system", value=collection,
                source_row_ref=ref, confidence="high",
            ))
            # Textile boxes are storage records, not Kapoor active works.
            observations.append(Observation(
                work_id=work_id, field="status", value="external",
                source_row_ref=ref, confidence="high",
            ))
            if contents:
                observations.append(Observation(
                    work_id=work_id, field="provenance_text",
                    value="\n".join(contents),
                    source_row_ref=ref, confidence="medium",
                ))
            observations.append(Observation(
                work_id=work_id, field="classification",
                value="Textile Arts",
                source_row_ref=ref, confidence="medium",
            ))

        return IngestResult(
            source=self._make_source(row_count=len(boxes)),
            observations=observations,
        )
