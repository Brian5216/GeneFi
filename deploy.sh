#!/bin/bash
# GeneFi - Gene + DeFi Evolution Engine
# One-click deployment script
# 一键部署脚本

set -e

echo "======================================"
echo " GeneFi - Gene + DeFi Evolution Engine"
echo " 基因金融"
echo "======================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required. Install it first."
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is required. Install it first."
    exit 1
fi

# Install Python dependencies
echo "[1/4] Installing Python dependencies..."
python3 -m pip install -r requirements.txt -q

# Install Node.js dependencies
echo "[2/4] Installing Node.js dependencies..."
npm install ws 2>/dev/null || true

# Create .env if not exists
if [ ! -f .env ]; then
    echo "[3/4] Creating .env from template..."
    cp .env.example .env 2>/dev/null || cat > .env << 'EOF'
# OKX API Keys (optional - works without for simulation mode)
OKX_API_KEY=
OKX_SECRET_KEY=
OKX_PASSPHRASE=

# Execution Mode: simulation | demo_api
EXECUTION_MODE=simulation

# Evolution Parameters
DEMO_MODE=true
EVOLUTION_POPULATION_SIZE=20
EVOLUTION_GENERATIONS=15
MUTATION_RATE=0.15
EOF
    echo "  Created .env - edit it to add OKX API keys for Demo Trading mode"
else
    echo "[3/4] .env already exists, skipping..."
fi

# Start services
echo "[4/4] Starting GeneFi..."
echo ""

# Kill existing processes
lsof -ti:8001 2>/dev/null | xargs kill 2>/dev/null || true
lsof -ti:8000 2>/dev/null | xargs kill 2>/dev/null || true

# Start Python backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8001 \
    --loop asyncio --http h11 --ws websockets &
BACKEND_PID=$!
echo "  Backend started (PID: $BACKEND_PID) on port 8001"

sleep 2

# Start Node.js proxy
node serve.js &
PROXY_PID=$!
echo "  Frontend proxy started (PID: $PROXY_PID) on port 8000"

echo ""
echo "======================================"
echo " GeneFi is running!"
echo " Open: http://localhost:8000"
echo ""
echo " Backend:  http://localhost:8001/api/status"
echo " Frontend: http://localhost:8000"
echo ""
echo " Press Ctrl+C to stop"
echo "======================================"

# Wait for Ctrl+C
trap "kill $BACKEND_PID $PROXY_PID 2>/dev/null; echo ''; echo 'GeneFi stopped.'; exit 0" INT TERM
wait
