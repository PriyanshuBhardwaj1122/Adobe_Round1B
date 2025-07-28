FROM  ubuntu:22.04

# Python, pip, poppler, tesseract
RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    poppler-utils tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /app/input /app/output
CMD ["python3", "src/main.py"]