# Dashboard

Interactive Streamlit dashboard for real-time trend monitoring, sentiment analysis, and insights visualization.

## 🎯 Purpose

- **Real-time Monitoring**: View live keyword performance and mention counts
- **Sentiment Analysis**: Visualize sentiment trends over time
- **AI Insights**: Access daily LLM-generated summaries
- **User Management**: Profile settings, keyword tracking, and alert preferences

## 📁 Structure

```
dashboard/
├── app.py                   # Main entry point (login/signup)
├── utils.py                 # Shared database & auth utilities
├── alerts.py                # Alert configuration helpers
├── conftest.py              # Pytest fixtures
├── reqs_dashboard.txt       # Python dependencies
├── pages/
│   ├── 1_Home.py            # Home dashboard with KPIs
│   ├── 2_Semantics.py       # Word clouds & network graphs
│   ├── 3_Daily_Summary.py   # Daily post summaries
│   ├── 3_Keyword_Deep_Dive.py # Individual keyword analysis
│   ├── 4_AI_Insights.py     # LLM-generated insights
│   └── 5_Profile.py         # User settings & keywords
├── queries/                 # SQL query files
├── styling/                 # HTML templates for UI components
├── art/                     # Logos and color palettes
└── images/                  # Static images
```

## 📊 Features

| Page | Description |
|------|-------------|
| **Home** | KPI metrics, recent posts, mention trends |
| **Semantics** | Word clouds, network visualization, keyword extraction |
| **Daily Summary** | Post volume by day, featured posts |
| **Keyword Deep Dive** | Individual keyword analysis, sentiment breakdown |
| **AI Insights** | LLM-generated daily summaries per user |
| **Profile** | Manage tracked keywords, email/alert preferences |

## 🚀 Deployment

### Environment Variables

```bash
DB_HOST=<RDS endpoint>
DB_PORT=5432
DB_NAME=<database name>
DB_USER=<database user>
DB_PASSWORD=<database password>
```

### Local Development

```bash
# Install dependencies
pip install -r reqs_dashboard.txt

# Set environment variables (or use .env file)
export DB_HOST=... DB_PORT=... DB_NAME=... DB_USER=... DB_PASSWORD=...

# Run the dashboard
streamlit run app.py
```

### Docker Deployment

```bash
# Build image
docker build -t trendfunnel-dashboard .

# Run container
docker run -p 8501:8501 \
  -e DB_HOST=... \
  -e DB_PORT=... \
  -e DB_NAME=... \
  -e DB_USER=... \
  -e DB_PASSWORD=... \
  trendfunnel-dashboard
```

### AWS Deployment (ECS)

The dashboard runs as an ECS Fargate service with:
- Container port: 8501
- Health check: `/healthz`
- Public ALB for external access

## 🔧 Dependencies

Key libraries:
- `streamlit` - Web framework
- `altair` - Declarative visualizations
- `pandas` - Data manipulation
- `wordcloud` - Word cloud generation
- `st-link-analysis` - Network graph visualization
- `yake` - Keyword extraction
