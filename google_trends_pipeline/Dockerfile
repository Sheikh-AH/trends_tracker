FROM public.ecr.aws/lambda/python:3.12

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY gt_extract.py .
COPY gt_transform.py .
COPY gt_load.py .
COPY gt_pipeline.py .

CMD ["gt_pipeline.handler"]