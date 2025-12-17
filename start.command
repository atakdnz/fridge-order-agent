#!/bin/bash
# SiparisAgent - Start Server
# Double-click this file to start the test server

cd "$(dirname "$0")"
source venv/bin/activate

echo "🚀 Starting SiparisAgent..."
echo "   Open http://localhost:5000 in your browser"
echo ""

python server.py
