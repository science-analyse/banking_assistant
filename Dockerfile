# Dockerfile for Real AI Banking Assistant
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies for AI models and audio processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    portaudio19-dev \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install additional AI dependencies
RUN pip install --no-cache-dir \
    torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Copy application code
COPY . .

# Create directories for AI models and data
RUN mkdir -p /app/vectordb /app/models /app/data

# Set environment variables
ENV PYTHONPATH=/app
ENV TRANSFORMERS_CACHE=/app/models
ENV HF_HOME=/app/models

# Expose ports
EXPOSE 8000 8501

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (can be overridden)
CMD ["python", "ai_fastapi_backend.py"]