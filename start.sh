#!/bin/bash
# GeneFi - One-click start script
# Starts both Python backend and Node.js proxy

cd "$(dirname "$0")"

echo "🧬 GeneFi - Gene + DeFi Evolution Engine"
echo "======================================="

# Kill existing processes
lsof -ti:8001 | xargs kill -9 2>/dev/null
lsof -ti:8000 | xargs kill -9 2>/dev/null
sleep 1

# Start Python backend
echo "▶ Starting Python backend on :8001..."
python3 -m uvicorn main:app --host 0.0.0.0 --port 8001 --loop asyncio --http h11 --ws websockets > /tmp/genefi_backend.log 2>&1 &
BACKEND_PID=$!
echo "  PID: $BACKEND_PID"

# Wait for backend
sleep 2
if curl -s -o /dev/null -w "" http://localhost:8001/api/status 2>/dev/null; then
    echo "  ✅ Backend ready"
else
    echo "  ❌ Backend failed to start"
    cat /tmp/genefi_backend.log
    exit 1
fi

# Start Node.js proxy
echo "▶ Starting Node.js proxy on :8000..."
node serve.js > /tmp/genefi_proxy.log 2>&1 &
PROXY_PID=$!
echo "  PID: $PROXY_PID"

sleep 1
if curl -s -o /dev/null -w "" http://localhost:8000/ 2>/dev/null; then
    echo "  ✅ Proxy ready"
else
    echo "  ❌ Proxy failed to start"
    cat /tmp/genefi_proxy.log
    exit 1
fi

echo ""
echo "🌐 Open http://localhost:8000"
echo "Press Ctrl+C to stop all services"
echo ""

# Wait and cleanup on exit
trap "kill $BACKEND_PID $PROXY_PID 2>/dev/null; echo '  Stopped.'" EXIT
wait
