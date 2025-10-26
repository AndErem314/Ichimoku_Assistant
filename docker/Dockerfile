FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for logs and state
RUN mkdir -p logs data/state

# Set timezone to UTC
ENV TZ=UTC
ENV PYTHONUNBUFFERED=1

# Run the monitor
CMD ["python", "-u", "monitor.py"]
