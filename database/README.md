# Database

PostgreSQL database schema and setup scripts for TrendFunnel.

## 🎯 Purpose

Central data store for all TrendFunnel data including:
- User accounts and preferences
- Tracked keywords
- Bluesky posts and sentiment scores
- Google Trends search volume data
- LLM-generated summaries

## 📁 Structure

```
database/
├── schema.sql    # Database schema definition
└── setup.sh      # Schema deployment script
```

## 🗄️ Schema Overview

| Table | Description |
|-------|-------------|
| `users` | User accounts with email, password hash, and notification preferences |
| `keywords` | Master list of all tracked keywords |
| `user_keywords` | Junction table linking users to their tracked keywords |
| `bluesky_posts` | Ingested posts with text, author, timestamp, and sentiment |
| `matches` | Links posts to matched keywords |
| `google_trends` | Search volume data from Google Trends |
| `llm_summary` | AI-generated summaries per user |

## 📊 Entity Relationships

```
users ─────┬──────> user_keywords <────── keywords
           │                                  │
           v                                  v
     llm_summary                        google_trends
                                              │
                                              v
                    bluesky_posts <────── matches
```

## 🚀 Deployment

### Prerequisites

- PostgreSQL 15+ database (e.g., AWS RDS)
- psql client installed
- Environment variables configured

### Environment Variables

Create a `.env` file:

```bash
DB_HOST=<RDS endpoint>
DB_PORT=5432
DB_NAME=<database name>
DB_USER=<database user>
DB_PASSWORD=<database password>
```

### Run Schema Setup

```bash
# Make script executable
chmod +x setup.sh

# Run the schema
./setup.sh
```

Or manually:

```bash
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f schema.sql
```

## 🔧 AWS Infrastructure

- **Service**: Amazon RDS (PostgreSQL 15)
- **Instance**: Configurable via Terraform (`db.t3.micro` for dev)
- **Storage**: GP2 with auto-scaling up to 100GB
- **Access**: VPC security group with port 5432

## 📝 Notes

- The schema uses `ON DELETE CASCADE` for referential integrity
- `post_uri` is the primary key for Bluesky posts (guaranteed unique)
- Sentiment scores are stored as VARCHAR to handle the compound score format
