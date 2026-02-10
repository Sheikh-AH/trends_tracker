# Alert System

Real-time spike detection and email alerting service for TrendFunnel. This Lambda function monitors keyword mention activity and sends email alerts to users when unusual spikes are detected.

## 🎯 Purpose

- **Spike Detection**: Compares keyword mentions in the last 5 minutes against the 24-hour average
- **Smart Alerting**: Only alerts users who have opted in and are tracking the spiking keyword
- **Rate Limiting**: Prevents alert fatigue by limiting to one alert per keyword per user per day

## 📁 Structure

```
alert_system/
├── alert_pipeline.py    # Main Lambda handler orchestrating detection and alerting
├── alert_detect.py      # Spike detection logic (5-min vs 24-hr comparison)
├── alert_send.py        # Email sending via AWS SES
├── alert_email.html     # HTML email template
├── Dockerfile           # Lambda container image
├── reqs_alert.txt       # Python dependencies
└── test_*.py            # Unit tests
```

## ⚙️ How It Works

1. **Fetch Keywords**: Retrieves all tracked keywords from the database
2. **Calculate Metrics**: For each keyword:
   - Count mentions in the last 5 minutes
   - Calculate average 5-minute count over last 24 hours
3. **Detect Spikes**: Flags keywords where recent activity exceeds the threshold
4. **Send Alerts**: Emails users who track the spiking keywords (via AWS SES)

## 🚀 Deployment

### Environment Variables

```bash
DB_HOST=<RDS endpoint>
DB_PORT=5432
DB_NAME=<database name>
DB_USER=<database user>
DB_PASSWORD=<database password>
AWS_REGION=<AWS region for SES>
```

### Build & Deploy (Docker)

```bash
# Build the Docker image
docker build -t alert-system .

# Tag for ECR
docker tag alert-system:latest <account>.dkr.ecr.<region>.amazonaws.com/c21-alert-system:latest

# Push to ECR
docker push <account>.dkr.ecr.<region>.amazonaws.com/c21-alert-system:latest
```

### Local Testing

```bash
# Install dependencies
pip install -r reqs_alert.txt

# Set environment variables
export DB_HOST=... DB_PORT=... DB_NAME=... DB_USER=... DB_PASSWORD=...

# Run locally
python alert_pipeline.py

# Run tests
pytest
```

## 🔧 AWS Infrastructure

- **Trigger**: EventBridge rule (every 5 minutes)
- **Runtime**: Lambda with container image
- **Email**: AWS SES for sending alerts
