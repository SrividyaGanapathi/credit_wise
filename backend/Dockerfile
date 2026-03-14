FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

EXPOSE 8000

CMD ["sh", "-c", "python -m alembic upgrade head && uvicorn app:app --host ${APP_HOST:-0.0.0.0} --port ${PORT:-8000}"]
