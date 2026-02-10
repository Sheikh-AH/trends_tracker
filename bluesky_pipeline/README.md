# Bluesky Pipeline

Real-time data ingestion pipeline for Bluesky social media posts. Streams posts from the Bluesky Jetstream firehose, filters by tracked keywords, performs sentiment analysis, and loads into the database.

## 🎯 Purpose

- **Real-time Streaming**: Connects to Bluesky's Jetstream WebSocket for live post data
- **Keyword Filtering**: Only processes posts matching user-tracked keywords
- **Sentiment Analysis**: Scores each post using VADER sentiment analysis
- **Continuous Ingestion**: Runs as a long-lived ECS service

## 📁 Structure

```
bluesky_pipeline/
├── pipeline.py              # Main ETL orchestrator
├── Dockerfile               # Container image for ECS
├── reqs_pipeline.txt        # Python dependencies
├── extract/
│   ├── extract.py           # Bluesky Jetstream WebSocket streaming
│   ├── conftest.py          # Pytest fixtures
│   └── test_extract.py      # Unit tests
├── transform/
│   ├── bs_transform.py      # Sentiment analysis & URI generation
│   └── test_bs_transform.py # Unit tests
└── load/
    └── bs_load.py           # Batch loading to PostgreSQL
```

## ⚙️ How It Works

1. **Extract**: Streams messages from Bluesky Jetstream WebSocket
   - Filters posts matching tracked keywords (refreshed every 60s)
   - Uses regex for flexible keyword matching
2. **Transform**: 
   - Adds VADER sentiment scores (-1 to +1)
   - Generates unique post URIs
3. **Load**: 
   - Batch inserts into `bluesky_posts` table
   - Records keyword matches in `matches` table

## 🚀 Deployment

### Environment Variables

```bash
DB_HOST=<RDS endpoint>
DB_PORT=5432
DB_NAME=<database name>
DB_USER=<database user>
DB_PASSWORD=<database password>
```

### Build & Deploy (Docker)

```bash
# Build the Docker image
docker build -t bluesky-pipeline .

# Tag for ECR
docker tag bluesky-pipeline:latest <account>.dkr.ecr.<region>.amazonaws.com/c21-bluesky-pipeline:latest

# Push to ECR
docker push <account>.dkr.ecr.<region>.amazonaws.com/c21-bluesky-pipeline:latest
```

### Local Development

```bash
# Install dependencies
pip install -r reqs_pipeline.txt

# Set environment variables (or use .env file)
export DB_HOST=... DB_PORT=... DB_NAME=... DB_USER=... DB_PASSWORD=...

# Run the pipeline
python pipeline.py

# Run tests
pytest
```

## 🔧 AWS Infrastructure

- **Runtime**: ECS Fargate (long-running container)
- **Networking**: Runs in VPC with RDS access
- **Data Source**: `wss://jetstream2.us-east.bsky.network`
