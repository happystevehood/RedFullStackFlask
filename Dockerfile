# Use slim base image with Python
FROM python:3.11-slim

# Set environment vars
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

# Create working directory
WORKDIR /app/src

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the application code
COPY ./src .

# Set environment mode dynamically (can be overridden)
ENV ENV_MODE=development

# Run with Gunicorn
CMD ["gunicorn", "-w", "4", "--preload", "--timeout", "90" , "-b", "0.0.0.0:5000", "app:app", "--worker-class gevent"]
