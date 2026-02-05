FROM public.ecr.aws/lambda/python:3.12

COPY reqs_alert.txt .
RUN pip install --no-cache-dir -r reqs_alert.txt

COPY alert_detect.py .
COPY alert_send.py .
COPY alert_pipeline.py .

CMD ["alert_pipeline.handler"]