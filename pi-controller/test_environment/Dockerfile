# GrowPi Test Environment - Dockerfile
# Allows running test environment in isolated container

FROM python:3.11-slim

# Metadata
LABEL maintainer="d.westermann@ol-mg.de"
LABEL description="GrowPi Test Environment (Simulation Mode)"
LABEL version="1.0.0"

# Set working directory
WORKDIR /app

# Install system dependencies (minimal - no hardware libs needed!)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better caching)
COPY test_environment/requirements.txt ./test_environment/
RUN pip install --no-cache-dir -r test_environment/requirements.txt

# Copy project files
COPY grow_pi ./grow_pi
COPY test_environment ./test_environment
COPY config ./config

# Set environment variables
ENV GROWPI_SIMULATION_MODE=1
ENV PYTHONUNBUFFERED=1

# Expose API port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:5000/api/health || exit 1

# Run test server
CMD ["python", "test_environment/run_local.py", "--host", "0.0.0.0", "--port", "5000"]
