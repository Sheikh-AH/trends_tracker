# LLM Summary

Daily AI-powered summary generation service using GPT via OpenRouter. Generates personalized trend insights for each user based on their tracked keywords.

## 🎯 Purpose

- **Personalized Insights**: Creates custom summaries for each user's tracked keywords
- **Multi-Source Analysis**: Combines Bluesky posts and Google Trends data
- **Daily Cadence**: Runs daily to provide fresh insights

## 📁 Structure

```
llm_summary/
├── main.py           # Lambda handler with LLM integration
├── Dockerfile        # Lambda container image
└── requirements.txt  # Python dependencies
```

## ⚙️ How It Works

1. **Fetch Users**: Retrieves all users from the database
2. **Gather Data**: For each user:
   - Gets their tracked keywords via `user_keywords`
   - Fetches recent Bluesky posts (via `matches`)
   - Fetches Google Trends search volume data
3. **Generate Summary**: Calls OpenRouter API with context
4. **Store Results**: Upserts summary into `llm_summary` table

## 🚀 Deployment

### Environment Variables

```bash
DB_HOST=<RDS endpoint>
DB_PORT=5432
DB_NAME=<database name>
DB_USER=<database user>
DB_PASSWORD=<database password>
OPENROUTER_API_KEY=<OpenRouter API key>
```

### Build & Deploy (Docker)

```bash
# Build the Docker image
docker build -t llm-summary .

# Tag for ECR
docker tag llm-summary:latest <account>.dkr.ecr.<region>.amazonaws.com/c21-llm-summary:latest

# Push to ECR
docker push <account>.dkr.ecr.<region>.amazonaws.com/c21-llm-summary:latest
```

### Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DB_HOST=... DB_PORT=... DB_NAME=... DB_USER=... DB_PASSWORD=...
export OPENROUTER_API_KEY=...

# Run locally
python main.py
```

## 🔧 AWS Infrastructure

- **Trigger**: EventBridge rule (daily)
- **Runtime**: Lambda with container image
- **LLM Provider**: OpenRouter (GPT-5-nano or similar)
- **Timeout**: Recommended 5+ minutes

## 💡 LLM Integration

The service uses OpenRouter for LLM access:
- **Endpoint**: `https://openrouter.ai/api/v1/chat/completions`
- **Model**: Configurable (e.g., GPT-5-nano for cost efficiency)
- **Context**: Recent posts, sentiment data, and trend volumes
