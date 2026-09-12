FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY data/ ./data/
COPY dashboard/ ./dashboard/
COPY reports/ ./reports/

WORKDIR /app/src
# Regenerate synthetic data at build time (swap for real log ingestion in production)
RUN python generate_logs.py && python health_score.py

EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
