#!/bin/bash

echo "🚀 Starting AI DevOps Assistant..."
docker compose -f docker-compose.yml -f docker-compose.live.yml up -d --build

echo ""
echo "✅ Containers are starting in the background!"
echo "It might take 30-60 seconds for all services to become healthy."
echo ""
echo "🌐 You can access the dashboard at: http://localhost:8000"
echo "📊 You can check service health at: http://localhost:8000/health"
echo ""
echo "To view logs, run: docker compose logs -f"
echo "To stop the app, run: ./stop.sh"
