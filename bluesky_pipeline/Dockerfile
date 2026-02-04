FROM python:3.14

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY reqs_pipeline.txt .
RUN pip install --no-cache-dir -r reqs_pipeline.txt

# Copy application code
COPY . .

# Run the pipeline
CMD ["python3", "pipeline.py"]