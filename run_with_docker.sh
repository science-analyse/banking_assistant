#!/bin/bash

echo "🐳 Starting AI Banking Assistant with Docker..."

# Build and start all services
docker-compose up -d --build

echo "✅ All services started!"
echo ""
echo "🌐 Access your AI Banking Assistant:"
echo "   Frontend: http://localhost:8501"
echo "   API Docs: http://localhost:8000/docs"
echo "   Vector DB: http://localhost:8002"
echo ""
echo "📊 Monitoring (optional):"
echo "   docker-compose --profile monitoring up -d"
echo "   Grafana: http://localhost:3000 (admin/admin)"
echo "   Prometheus: http://localhost:9090"
echo ""
echo "🔧 View logs:"
echo "   docker-compose logs -f ai-backend"
echo "   docker-compose logs -f ai-frontend"
echo ""
echo "🛑 Stop all services:"
echo "   docker-compose down"
