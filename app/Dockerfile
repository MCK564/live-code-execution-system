FROM python:3.12-slim

WORKDIR /app

ENV PYTHONPATH=/app

COPY requirements.txt .

RUN apt-get update && apt-get install -y docker.io \
    && pip install --no-cache-dir -r requirements.txt \
    && rm -rf /var/lib/apt/lists/*



COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001",  "--reload"]
