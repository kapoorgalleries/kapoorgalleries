.PHONY: init ingest consolidate report all clean test

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

clean:
	rm -f data/inventory.db data/master.csv data/master_long.csv data/conflicts.csv data/gaps.csv data/artsy_upload.csv
	rm -f reports/*.md
