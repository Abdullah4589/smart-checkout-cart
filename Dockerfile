FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Pre-download the YOLO-World weights + CLIP text encoder at build time so
# the image is self-contained and the first real request doesn't stall on a
# multi-hundred-MB download.
RUN python -c "import sys; sys.path.insert(0, 'backend'); import config; from ultralytics import YOLOWorld; YOLOWorld(config.MODEL_WEIGHTS)"

CMD ["sh", "start.sh"]
