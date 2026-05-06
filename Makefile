.PHONY: init ingest consolidate report all clean test stats lint conflicts gaps

PY ?= python3

init:
	$(PY) -m src.cli init-db

# Run every ingester registered in catalog/sources.yaml.
ingest:
	$(PY) -m src.cli ingest

# Run a single ingester: make ingest-one SRC=artsy_csv FILE=data/raw/Artsy_2-16-2026.csv
ingest-one:
	$(PY) -m src.cli ingest-one --type=$(SRC) --file=$(FILE)

consolidate:
	$(PY) -m src.cli consolidate

report:
	$(PY) -m src.cli report

# Full pipeline.
all: init ingest consolidate report
	@echo
	@echo "Done. Inspect:"
	@echo "  data/inventory.db"
	@echo "  data/master.csv"
	@echo "  data/conflicts.csv"
	@echo "  data/gaps.csv"
	@echo "  data/artsy_upload.csv"
	@echo "  reports/coverage_report.md"
	@echo "  reports/gaps_report.md"
	@echo "  reports/provenance_report.md"

test:
	$(PY) -m pytest

# Read-only ops (after `make all`) — handy shortcuts.
stats:
	$(PY) -m src.cli stats
lint:
	$(PY) -m src.cli lint
conflicts:
	$(PY) -m src.cli conflicts
gaps:
	$(PY) -m src.cli gaps --max-missing 1
sources:
	$(PY) -m src.cli source list

# Full system health snapshot.
health: stats lint
	@echo "==== source list ===="
	@$(PY) -m src.cli source list || true
	@echo "==== conflicts (top 5) ===="
	@$(PY) -m src.cli conflicts --limit 5 || true
	@echo "==== artsy upload validation ===="
	@$(PY) -m src.cli check-artsy || true
	@echo "==== rule suggestions (top 5) ===="
	@$(PY) -m src.cli suggest-rules --min-support 10 | head -10 || true

# Guided tour of the system's main features.  Read-only: doesn't modify data.
demo:
	@echo "===== Kapoor Galleries · Inventory · guided tour ====="
	@echo
	@echo "===== make stats ====="
	@$(PY) -m src.cli stats
	@echo "===== make lint ====="
	@$(PY) -m src.cli lint
	@echo "===== make conflicts (top 5) ====="
	@$(PY) -m src.cli conflicts --limit 5
	@echo "===== kg-inv show KG-1000 ====="
	@$(PY) -m src.cli show KG-1000
	@echo "===== kg-inv search 'khanjar' ====="
	@$(PY) -m src.cli search khanjar
	@echo "===== make check-artsy ====="
	@$(PY) -m src.cli check-artsy
	@echo
	@echo "===== try interactively: ====="
	@echo "  python -m src.cli triage"
	@echo "  python -m src.cli resolve KG-1000 classification \"Drawing, …\" --by you@…"
	@echo "  python -m src.cli suggest-rules"
	@echo "  python -m src.cli export-filtered --classification Sculpture --out my.csv"
	@echo

clean:
	rm -f data/inventory.db data/master.csv data/master_long.csv data/conflicts.csv data/gaps.csv data/artsy_upload.csv
	rm -f reports/*.md
