FROM public.ecr.aws/lambda/python:3.12

WORKDIR ${LAMBDA_TASK_ROOT}

# Install dependencies
COPY reqs_report.txt .
RUN pip install --no-cache-dir -r reqs_report.txt

# Copy application code
COPY report_data.py .
COPY report.html .
COPY gen_html_report.py .
COPY main.py .

CMD ["main.lambda_handler"]