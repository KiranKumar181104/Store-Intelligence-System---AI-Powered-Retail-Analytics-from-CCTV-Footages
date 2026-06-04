# Store Intelligence Design

## Architecture Overview

This repository is organized as a small end-to-end analytics platform:

- `pipeline/` handles CCTV video ingestion, tracking, and event emission.
- `app/` hosts the FastAPI service that ingests events, stores them in SQLite, and exposes analytics endpoints.
- `dashboard/` provides a Streamlit dashboard that consumes the API.
- `scripts/` contains utility scripts such as event replayers.
- `data/` stores static assets needed at runtime.

## Key Components

### Detection Pipeline

The pipeline is intentionally lightweight in this version. It accepts one camera video, generates a single event, and writes JSONL output. This supports the repository's file layout and gives a template for future model integration.

### API Layer

The API exposes real-time store analytics:

- `/events/ingest`
- `/stores/{store_id}/metrics`
- `/stores/{store_id}/funnel`
- `/stores/{store_id}/heatmap`
- `/stores/{store_id}/anomalies`
- `/health`

The backend uses SQLAlchemy with SQLite to keep the service self-contained and easy to deploy via Docker.

### Dashboard

The dashboard is a Streamlit app that polls the API and renders live metrics, funnel charts, heatmaps, and anomaly alerts.

## Deployment

The repository contains production-ready Docker artifacts:

- `Dockerfile` for the API
- `Dockerfile.dashboard` for the dashboard
- `docker-compose.yml` to orchestrate both services

The architecture is designed so the API, dashboard, and data volumes are separated cleanly.
