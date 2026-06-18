"""Site-wide metadata feed for the public website.

Reads ``data/site.yaml`` (curator-maintained) and emits
``data/site.json`` — gallery name, address, contact, hours, social,
memberships, navigation.  Consumed by the SPA for footer/header,
contact page, and structured-data (JSON-LD) markup.

Designed to be a no-op when ``site.yaml`` is missing — keeps
``make report`` deterministic on fresh checkouts.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore[import-untyped]
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


_SCHEMA_VERSION = 1


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _empty(note: str) -> dict:
    return {
        "schema_version": _SCHEMA_VERSION,
        "generated_at": _now_utc(),
        "_note": note,
    }


def export_site(
    *,
    config_yaml: Path | str = "data/site.yaml",
    out_path: Path | str = "data/site.json",
) -> tuple[Path, bool]:
    """Build data/site.json from data/site.yaml.

    Returns (out_path, ok) where ``ok`` is True iff the YAML was
    present, parseable, and produced a non-empty payload.
    """
    cfg = Path(config_yaml)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if not cfg.exists():
        out.write_text(json.dumps(
            _empty(f"{cfg} not present"), indent=2, ensure_ascii=False) + "\n")
        return out, False
    if not HAS_YAML:
        out.write_text(json.dumps(
            _empty("PyYAML not installed; pip install pyyaml"),
            indent=2, ensure_ascii=False) + "\n")
        return out, False

    data: dict[str, Any] = yaml.safe_load(cfg.read_text()) or {}

    addr = data.get("address") or {}
    gallery = data.get("gallery") or {}
    # JSON-LD payload — drop-in for the site's <head> for SEO.
    json_ld = {
        "@context": "https://schema.org",
        "@type": "ArtGallery",
        "name": gallery.get("name"),
        "legalName": gallery.get("legal_name"),
        "description": (gallery.get("description") or "").strip() or None,
        "url": "https://kapoorgalleries.com",
        "telephone": (data.get("contact") or {}).get("phone_us"),
        "email": (data.get("contact") or {}).get("email_general"),
        "address": {
            "@type": "PostalAddress",
            "streetAddress": " ".join(filter(None, [
                addr.get("street"), addr.get("street_2"),
            ])).strip(),
            "addressLocality": addr.get("city"),
            "addressRegion":   addr.get("state"),
            "postalCode":      addr.get("postal_code"),
            "addressCountry":  addr.get("country_code"),
        },
        "geo": (
            {
                "@type": "GeoCoordinates",
                "latitude":  addr.get("lat"),
                "longitude": addr.get("lng"),
            } if (addr.get("lat") and addr.get("lng")) else None
        ),
        "openingHoursSpecification": [
            {
                "@type": "OpeningHoursSpecification",
                "dayOfWeek": h.get("day"),
                "opens":     h.get("opens") or None,
                "closes":    h.get("closes") or None,
            }
            for h in (data.get("hours") or []) if h.get("opens")
        ],
    }

    out_payload = {
        "schema_version": _SCHEMA_VERSION,
        "generated_at":   _now_utc(),
        "gallery":        gallery or None,
        "contact":        data.get("contact"),
        "address":        addr or None,
        "hours":          data.get("hours"),
        "social":         data.get("social"),
        "memberships":    data.get("memberships"),
        "team":           data.get("team"),
        "nav":            data.get("nav"),
        "json_ld":        json_ld,
    }
    out.write_text(json.dumps(out_payload, indent=2, ensure_ascii=False) + "\n")
    return out, True
