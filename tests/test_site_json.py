"""Tests for the site-metadata exporter (data/site.json)."""

from pathlib import Path

import json

from src.exporters import site_json


def test_site_emits_jsonld_and_payload(tmp_path: Path):
    cfg = tmp_path / "site.yaml"
    cfg.write_text(
        "gallery:\n"
        "  name: Kapoor Galleries\n"
        "  description: Test description.\n"
        "contact:\n"
        "  email_general: info@example.com\n"
        "  phone_us: +1 555 0123\n"
        "address:\n"
        "  street: 34 East 67th\n"
        "  city: New York\n"
        "  state: NY\n"
        "  postal_code: '10065'\n"
        "  country_code: US\n"
        "  lat: 40.7677\n"
        "  lng: -73.9667\n"
        "hours:\n"
        "  - { day: Monday, opens: '10:00', closes: '18:00', note: '' }\n"
        "  - { day: Sunday, opens: '', closes: '', note: closed }\n"
        "nav:\n"
        "  - { label: Works, url: /works }\n"
    )
    out, ok = site_json.export_site(
        config_yaml=cfg, out_path=tmp_path / "site.json")
    assert ok is True
    feed = json.loads(out.read_text())
    assert feed["schema_version"] == 1
    assert feed["gallery"]["name"] == "Kapoor Galleries"
    assert feed["contact"]["email_general"] == "info@example.com"
    jl = feed["json_ld"]
    assert jl["@type"] == "ArtGallery"
    assert jl["address"]["addressLocality"] == "New York"
    assert jl["geo"]["latitude"] == 40.7677
    # Sunday is closed (opens=='') -> filtered from openingHours.
    assert len(jl["openingHoursSpecification"]) == 1


def test_site_no_op_when_yaml_missing(tmp_path: Path):
    out, ok = site_json.export_site(
        config_yaml=tmp_path / "absent.yaml",
        out_path=tmp_path / "site.json")
    feed = json.loads(out.read_text())
    assert ok is False
    assert "_note" in feed
    assert "not present" in feed["_note"]
