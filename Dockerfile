# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies including Chrome
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    wget \
    gnupg \
    unzip \
    curl \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Chromium (works on ARM)
RUN apt-get update && \
    apt-get install -y chromium chromium-driver && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements_scraper.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements_scraper.txt

# Copy the scraper script
COPY scrape_bank_of_baku.py .

# Create output directory
RUN mkdir -p /app/scraped_data

# Set volume for output data
VOLUME ["/app/scraped_data"]

# Run the scraper when container launches
CMD ["python", "scrape_bank_of_baku.py"]
