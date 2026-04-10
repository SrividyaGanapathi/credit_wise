FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (layer-cached until requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy pipeline source
COPY . .

# Cloud Run Jobs expect the container to exit 0 on success
CMD ["python", "run_discovery.py"]
