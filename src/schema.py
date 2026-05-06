"""SQL DDL and pydantic models for the inventory pipeline.

The long-format `observations` table is the durable record. Every value any
source ever emitted survives forever, so we can flag conflicts (never silently
merge) and rebuild `works` idempotently.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

CANONICAL_FIELDS: tuple[str, ...] = (
    "title",
    "artist",
    "year",
    "period_school_region",
    "classification",
    "medium",
    "materials",
    "height_in",
    "width_in",
    "depth_in",
    "price_usd",
    "status",
    "provenance_text",
    "exhibitions",
    "publications",
    "signature",
    "coa_status",
    "primary_image_url",
    "primer_uuid",
    "location",
    "external_id",
    "external_id_system",
    "artsy_eligibility",
)

ARTSY_REQUIRED_FIELDS: tuple[str, ...] = (
    "title",
    "classification",
    "medium",
    "primary_image_url",
)

DDL = """
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    drive_file_id TEXT,
    drive_file_path TEXT,
    file_modified_at TEXT,
    extracted_at TEXT NOT NULL,
    row_count INTEGER,
    parser_version TEXT,
    UNIQUE(name, extracted_at)
);

CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id TEXT NOT NULL,
    field TEXT NOT NULL,
    value TEXT,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    source_row_ref TEXT,
    confidence TEXT NOT NULL DEFAULT 'medium',
    observed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_obs_work_field ON observations(work_id, field);
CREATE INDEX IF NOT EXISTS ix_obs_source ON observations(source_id);

CREATE TABLE IF NOT EXISTS works (
    work_id TEXT PRIMARY KEY,
    title TEXT,
    artist TEXT,
    year INTEGER,
    period_school_region TEXT,
    classification TEXT,
    medium TEXT,
    materials TEXT,
    height_in REAL,
    width_in REAL,
    depth_in REAL,
    price_usd REAL,
    status TEXT,
    provenance_text TEXT,
    exhibitions TEXT,
    publications TEXT,
    signature TEXT,
    coa_status TEXT,
    primary_image_url TEXT,
    primer_uuid TEXT,
    location TEXT,
    external_id TEXT,
    external_id_system TEXT,
    artsy_eligibility TEXT,
    has_conflict INTEGER NOT NULL DEFAULT 0,
    conflict_fields TEXT,
    canonical_updated_at TEXT
);

CREATE TABLE IF NOT EXISTS work_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id TEXT NOT NULL,
    image_url TEXT,
    drive_file_id TEXT,
    bytes INTEGER,
    is_placeholder INTEGER NOT NULL DEFAULT 0,
    source_id INTEGER REFERENCES sources(id)
);
CREATE INDEX IF NOT EXISTS ix_img_work ON work_images(work_id);

DROP VIEW IF EXISTS v_conflicts;
CREATE VIEW v_conflicts AS
SELECT work_id,
       field,
       COUNT(DISTINCT value) AS distinct_values,
       GROUP_CONCAT(value, ' || ') AS values_seen
FROM (SELECT DISTINCT work_id, field, value FROM observations WHERE value IS NOT NULL AND value != '')
GROUP BY work_id, field
HAVING distinct_values > 1;
"""


class Observation(BaseModel):
    work_id: str
    field: str
    value: Optional[str]
    source_row_ref: Optional[str] = None
    confidence: str = "medium"
    observed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SourceRecord(BaseModel):
    name: str
    type: str
    drive_file_id: Optional[str] = None
    drive_file_path: Optional[str] = None
    file_modified_at: Optional[str] = None
    extracted_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    row_count: Optional[int] = None
    parser_version: str = "0.1"


class WorkImage(BaseModel):
    work_id: str
    image_url: Optional[str] = None
    drive_file_id: Optional[str] = None
    bytes: Optional[int] = None
    is_placeholder: bool = False
