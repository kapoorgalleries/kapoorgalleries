# Kapoor Galleries backend API.
#
# Serves the inventory pipeline's generated JSON feeds (committed under
# data/) as a queryable REST API.  The image bakes in whatever feeds
# are present at build time; redeploy after `make report` to refresh,
# or mount a volume at /app/data and set KG_API_DATA_DIR.
FROM python:3.11-slim

WORKDIR /app

# Install only what the API needs — the heavy ingest deps (pdfplumber,
# pandas, openpyxl) aren't required to serve feeds.
COPY pyproject.toml ./
RUN pip install --no-cache-dir \
      "fastapi>=0.110" "uvicorn[standard]>=0.27" "PyYAML>=6.0"

# App code + the generated feeds.
COPY src ./src
COPY data ./data

ENV KG_API_DATA_DIR=/app/data \
    KG_API_CORS_ORIGINS=* \
    PORT=8000

EXPOSE 8000

# Honor $PORT (Render/Fly/Cloud Run inject it); default 8000.
CMD ["sh", "-c", "uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
