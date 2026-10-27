#!/bin/bash

echo "🛑 Stopping AI DevOps Assistant..."
docker compose -f docker-compose.yml -f docker-compose.live.yml down

echo ""
echo "✅ All services stopped successfully!"
