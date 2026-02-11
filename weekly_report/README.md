# Weekly Report

Automated weekly email report generation and delivery service for TrendFunnel users.

## 🎯 Purpose

- **Comprehensive Reports**: Generates HTML email reports with keyword performance data
- **User-Specific**: Each user receives a report based on their tracked keywords
- **Weekly Cadence**: Triggered weekly via EventBridge

## 📁 Structure

```
weekly_report/
├── main.py              # Lambda handler & email sending
├── report_data.py       # Data fetching from database
├── gen_html_report.py   # HTML report generation
├── report.html          # HTML email template
├── Dockerfile           # Lambda container image
├── reqs_report.txt      # Python dependencies
└── test_report_data.py  # Unit tests
```

## ⚙️ How It Works

1. **Fetch Users**: Gets all users with `send_email = true`
2. **Gather Data**: For each user:
   - Gets their tracked keywords
   - Fetches post counts (this week vs last week)
   - Calculates sentiment breakdown
   - Gets top posts per keyword
3. **Generate Report**: Builds personalized HTML email
4. **Send Email**: Delivers via AWS SES

## 📊 Report Contents

Each weekly report includes:
- **Keyword Performance**: Mention counts with week-over-week comparison
- **Sentiment Breakdown**: Positive/Neutral/Negative distribution
- **Top Posts**: Featured posts for each keyword
- **Trend Indicators**: Up/down arrows for momentum

## 🚀 Deployment

### Environment Variables

```bash
DB_HOST=<RDS endpoint>
DB_PORT=5432
DB_NAME=<database name>
DB_USER=<database user>
DB_PASSWORD=<database password>
AWS_REGION=<AWS region for SES>
SENDER_EMAIL=<verified SES sender email>
```

### Build & Deploy (Docker)

```bash
# Build the Docker image
docker build -t weekly-report .

# Tag for ECR
docker tag weekly-report:latest <account>.dkr.ecr.<region>.amazonaws.com/c21-weekly-report:latest

# Push to ECR
docker push <account>.dkr.ecr.<region>.amazonaws.com/c21-weekly-report:latest
```

### Local Testing

```bash
# Install dependencies
pip install -r reqs_report.txt

# Set environment variables
export DB_HOST=... DB_PORT=... DB_NAME=... DB_USER=... DB_PASSWORD=...
export AWS_REGION=... SENDER_EMAIL=...

# Run locally
python main.py

# Run tests
pytest
```

## 🔧 AWS Infrastructure

- **Trigger**: EventBridge rule (weekly, e.g., Monday 9am)
- **Runtime**: Lambda with container image
- **Email**: AWS SES (sender must be verified)
- **Assets**: Logo hosted on S3

## 📧 Email Configuration

- Sender email must be verified in SES
- For production, request SES production access (sandbox limits apply)
- HTML emails are responsive and styled inline
