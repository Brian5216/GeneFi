FROM python:3.11-slim AS backend

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py main.py ./
COPY dtes/ dtes/
COPY static/ static/

EXPOSE 8001
CMD ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--loop", "asyncio", "--http", "h11", "--ws", "websockets"]

FROM node:20-alpine AS proxy

WORKDIR /app
COPY package.json .
RUN npm install --production
COPY serve.js .
COPY static/ static/

EXPOSE 8000
CMD ["node", "serve.js"]
