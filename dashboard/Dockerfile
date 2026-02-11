# Use the official Python image as a base
FROM python:latest


# Copy requirements file
COPY reqs_dashboard.txt .

# Install Python dependencies
RUN pip install --upgrade pip \
    && pip install -r reqs_dashboard.txt

# Copy the dashboard app code
COPY . .

# Set the entrypoint to run the Streamlit app
CMD ["streamlit", "run", "app.py"]
