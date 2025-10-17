#!/bin/bash
# Quick deployment script for Bank of Baku RAG Assistant

set -e

echo "═══════════════════════════════════════════════════════════"
echo "🚀 Bank of Baku RAG Assistant - Deployment Script"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install it first."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo ""
    read -p "Enter your Gemini API key: " api_key
    echo "LLM_API_KEY=$api_key" > .env
    echo "✅ Created .env file"
else
    echo "✅ .env file found"
fi

echo ""
echo "Building Docker image..."
docker-compose build

echo ""
echo "Starting container..."
docker-compose up -d

echo ""
echo "Waiting for service to be healthy..."
sleep 5

# Check health
if curl -s http://localhost:5001/api/health > /dev/null 2>&1; then
    echo "✅ Service is healthy!"
else
    echo "⚠️  Service might still be starting. Check logs with:"
    echo "   docker-compose logs -f"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "🎉 Deployment Complete!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "📍 Application URL: http://localhost:5001"
echo "📊 Health Check:    http://localhost:5001/api/health"
echo ""
echo "Useful commands:"
echo "  • View logs:    docker-compose logs -f"
echo "  • Stop:         docker-compose down"
echo "  • Restart:      docker-compose restart"
echo ""
echo "Open http://localhost:5001 in your browser to start!"
echo ""
