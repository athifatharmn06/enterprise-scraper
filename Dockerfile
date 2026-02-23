FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (already in the image, but ensures matching version)
RUN playwright install chromium

# Copy app code
COPY . .

# Run FastAPI by default
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
