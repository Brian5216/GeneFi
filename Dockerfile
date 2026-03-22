FROM python:3.11-slim

WORKDIR /app

# Install Node.js
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Node dependencies
COPY package.json .
RUN npm install --production 2>/dev/null || true

# Copy app
COPY config.py main.py serve.js mcp_proxy.js ./
COPY dtes/ dtes/
COPY static/ static/

# Create logs dir
RUN mkdir -p logs

# Single port for Render/Railway (proxy handles everything)
ENV PORT=8000
EXPOSE 8000

# Start both services
CMD bash -c "\
    python3 -m uvicorn main:app --host 0.0.0.0 --port 8001 --loop asyncio --http h11 --ws websockets & \
    sleep 2 && \
    node serve.js"
