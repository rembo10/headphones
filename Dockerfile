# Use Python 3.11 as base image for better compatibility and security
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HEADPHONES_HOME=/headphones \
    DATA_DIR=/data

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p ${HEADPHONES_HOME} ${DATA_DIR}

# Set working directory
WORKDIR ${HEADPHONES_HOME}

# Copy the headphones application
COPY . ${HEADPHONES_HOME}/

# Create a non-root user to run the application
RUN useradd -m -u 1000 headphones && \
    chown -R headphones:headphones ${HEADPHONES_HOME} ${DATA_DIR}

# Switch to non-root user
USER headphones

# Expose the default port used by CherryPy
EXPOSE 8181

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8181/ || exit 1

# Run the application
CMD ["python", "Headphones.py", "--host", "0.0.0.0", "--datadir", "/data", "--nolaunch"]
