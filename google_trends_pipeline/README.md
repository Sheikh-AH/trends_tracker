# Google Trends Pipeline

ETL pipeline for fetching search volume data from Google Trends for tracked keywords.

## 🎯 Purpose

- **Search Volume Tracking**: Fetches Google Trends interest data for all tracked keywords
- **Daily Updates**: Runs daily via EventBridge to capture trending data
- **UK-Focused**: Configured for UK region with 7-day lookback period

## 📁 Structure

```
google_trends_pipeline/
├── gt_pipeline.py       # Main Lambda handler (ETL orchestrator)
├── gt_extract.py        # Fetches keywords from DB & queries Google Trends API
├── gt_transform.py      # Data transformation and validation
├── gt_load.py           # Loads data into PostgreSQL
├── Dockerfile           # Lambda container image
├── reqs_gt_pipeline.txt # Python dependencies
└── test_*.py            # Unit tests
```

## ⚙️ How It Works

1. **Extract**:
   - Fetches all tracked keywords from the database
   - Queries Google Trends API in batches of 5 (API limit)
   - Gets 7-day interest data for each keyword (UK region)
   - Calculates average search volume

2. **Transform**:
   - Validates and cleans data
   - Adds timestamps

3. **Load**:
   - Upserts records into `google_trends` table

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
docker build -t gt-pipeline .

# Tag for ECR
docker tag gt-pipeline:latest <account>.dkr.ecr.<region>.amazonaws.com/c21-gt-pipeline:latest

# Push to ECR
docker push <account>.dkr.ecr.<region>.amazonaws.com/c21-gt-pipeline:latest
```

### Local Testing

```bash
# Install dependencies
pip install -r reqs_gt_pipeline.txt

# Set environment variables
export DB_HOST=... DB_PORT=... DB_NAME=... DB_USER=... DB_PASSWORD=...

# Run locally
python gt_pipeline.py

# Run tests
pytest
```

## 🔧 AWS Infrastructure

- **Trigger**: EventBridge rule (daily)
- **Runtime**: Lambda with container image
- **Timeout**: Recommended 5+ minutes (API rate limiting)

## ⚠️ Rate Limiting

Google Trends API has rate limits. The pipeline:
- Processes keywords in batches of 5
- Adds 2-second delays between batches
- Handles errors gracefully to avoid partial failures
