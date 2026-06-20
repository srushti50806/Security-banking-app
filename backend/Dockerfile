FROM python:3.10-slim

WORKDIR /app

# Install system dependencies if required for ML packages (lightgbm/scikit)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

COPY . .

EXPOSE 5000

# Start Gunicorn server pointing to app.app
CMD ["gunicorn", "-b", "0.0.0.0:5000", "--workers", "2", "app:app"]
