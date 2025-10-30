# Dockerfile for Auto-TDD Execution Environment
FROM python:3.10-alpine

# Install system dependencies
RUN apk add --no-cache \
    docker-cli \
    git \
    gcc \
    musl-dev \
    linux-headers

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p artifacts logs .cache

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose ports (if needed for future web interface)
EXPOSE 8000

# Entry point
ENTRYPOINT ["python", "cli.py"]

# Default command
CMD ["--help"]
