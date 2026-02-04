FROM public.ecr.aws/lambda/python:3.12

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alert_detect.py .
COPY alert_send.py .
COPY alert_pipeline.py .

CMD ["alert_pipeline.handler"]