# Inventory viewer

A single static HTML page that renders `data/master.json` as a sortable,
filterable inventory browser.  No server required.

## Usage

After `make all` has produced `data/master.json`:

```bash
# Open the file in your default browser:
$ open viewer/index.html        # macOS
$ xdg-open viewer/index.html    # Linux
$ start viewer/index.html       # Windows

# Or serve it locally if your browser blocks local fetch:
$ cd viewer && python3 -m http.server 8000
$ open http://localhost:8000
```

## What it does

- Free-text filter (title / classification / medium / KG-# / materials / year)
- Classification dropdown
- "Conflicts only" toggle (renders red)
- "Artsy-eligible only" toggle (works that pass the upload filter)
- Click any column header to sort
- Cap of 500 rows in the DOM at a time for speed

## Pointing at a different JSON

Append `?data=<url>` to load from a custom URL — useful if you've
generated a filtered subset:

```bash
$ python -m src.cli export-filtered \
    --classification Sculpture --out data/sculptures.csv
$ python -c "
import csv, json
rows = list(csv.DictReader(open('data/sculptures.csv')))
json.dump(rows, open('viewer/sculptures.json','w'))"
$ open 'viewer/index.html?data=sculptures.json'
```
