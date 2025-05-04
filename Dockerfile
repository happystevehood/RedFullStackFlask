# Use an official lightweight Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create and set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the app code
COPY . .

# Expose port (match .env)
EXPOSE 5000

# Default command (override in compose or deploy)
CMD ["gunicorn", "-b", "0.0.0.0:5000", "init:app"]