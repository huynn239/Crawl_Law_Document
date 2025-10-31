#!/bin/bash
# Test API server

echo "Testing API server..."

# Test health endpoint
echo "1. Testing /health..."
curl -s http://localhost:8000/health | jq .

# Test download-pending endpoint
echo -e "\n2. Testing /download-pending..."
curl -s -X POST "http://localhost:8000/download-pending?limit=5" | jq .

echo -e "\n✓ API tests completed!"
