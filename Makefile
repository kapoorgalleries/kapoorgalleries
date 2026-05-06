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
	@$(PY) -m src.cli overview
	@echo
	@$(PY) -m src.cli check-artsy

test:
	$(PY) -m pytest

# Read-only ops (after `make all`) — handy shortcuts.
overview:
	$(PY) -m src.cli overview
coverage:
	$(PY) -m src.cli coverage
viewer:
	@echo "Open viewer/index.html in your browser, or:"
	@echo "  cd viewer && python3 -m http.server 8000"
	@echo "Then visit: http://localhost:8000"
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
	@echo "==== price distribution ===="
	@$(PY) -m src.cli prices || true
	@echo "==== conflicts (top 5) ===="
	@$(PY) -m src.cli conflicts --limit 5 || true
	@echo "==== artsy upload validation ===="
	@$(PY) -m src.cli check-artsy || true
	@echo "==== duplicate titles ===="
	@$(PY) -m src.cli duplicate-titles --limit 5 || true
	@echo "==== rule suggestions (top 5) ===="
	@$(PY) -m src.cli suggest-rules --min-support 10 | head -10 || true

# Guided tour of the system's main features.  Read-only: doesn't modify data.
demo:
	@echo "===== Kapoor Galleries · Inventory · guided tour ====="
	@echo
	@$(PY) -m src.cli overview
	@echo "===== kg-inv coverage ====="
	@$(PY) -m src.cli coverage
	@echo "===== kg-inv classifications ====="
	@$(PY) -m src.cli classifications
	@echo "===== kg-inv prices ====="
	@$(PY) -m src.cli prices
	@echo "===== kg-inv conflicts (top 5) ====="
	@$(PY) -m src.cli conflicts --limit 5
	@echo "===== kg-inv lint ====="
	@$(PY) -m src.cli lint
	@echo "===== kg-inv show KG-1000 ====="
	@$(PY) -m src.cli show KG-1000
	@echo "===== kg-inv check-artsy ====="
	@$(PY) -m src.cli check-artsy
	@echo
	@echo "===== try interactively: ====="
	@echo "  kg-inv triage"
	@echo "  kg-inv resolve KG-1000 classification \"Drawing, …\" --by you@…"
	@echo "  kg-inv suggest-rules"
	@echo "  kg-inv export-filtered --classification Sculpture --out my.csv"
	@echo

# Watch mode: rebuild on changes to rules / sources / data/raw/.
# Requires `inotifywait` (apt: inotify-tools).
watch:
	@command -v inotifywait >/dev/null || { \
	  echo "inotify-tools not installed.  Run: sudo apt install inotify-tools"; exit 1; }
	@echo "watching data/auto_resolution_rules.yaml, data/human_resolutions.yaml, catalog/sources.yaml, data/raw/ ..."
	@while true; do \
	  $(MAKE) all; \
	  echo; echo "Waiting for changes (Ctrl+C to stop)..."; \
	  inotifywait -qr -e modify -e create -e delete \
	    data/auto_resolution_rules.yaml data/human_resolutions.yaml \
	    catalog/sources.yaml data/raw/ src/ 2>/dev/null; \
	done

clean:
	rm -f data/inventory.db data/master.csv data/master_long.csv data/conflicts.csv data/gaps.csv data/artsy_upload.csv
	rm -f reports/*.md
