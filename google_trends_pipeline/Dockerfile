FROM public.ecr.aws/lambda/python:3.12

COPY reqs_gt_pipeline.txt .
RUN pip install --no-cache-dir -r reqs_gt_pipeline.txt

COPY gt_extract.py .
COPY gt_transform.py .
COPY gt_load.py .
COPY gt_pipeline.py .

CMD ["gt_pipeline.handler"]