# Backend Dockerfile for TempoExpenseAI
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libomp-dev \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create directory for database and models
RUN mkdir -p /app/ml/models /app/ml/data

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "main.py"]
