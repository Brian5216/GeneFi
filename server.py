"""GeneFi Standalone Server - Pure Python stdlib HTTP + WebSocket server.
No external dependencies required for the preview sandbox.
"""
import asyncio
import json
import os
import sys
import time
import hashlib
import base64
import struct
import http.server
import threading
import socket
from urllib.parse import urlparse

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from config import Config
from dtes.core.evolution import EvolutionEngine
from dtes.core.strategy import StrategyGene
from dtes.protocol.a2a import MessageBus, A2AMessage, MessageType
from dtes.agents.predictor import PredictorAgent
from dtes.agents.executor import ExecutorAgent
from dtes.agents.judge import JudgeAgent
from dtes.okx.onchain_os import OnchainOSClient

# ─── Global State ─────────────────────────────────
config = Config()
bus = MessageBus()
engine = EvolutionEngine(config)
okx_client = OnchainOSClient(config)
predictor = PredictorAgent(bus, config)
executor = ExecutorAgent(bus, config)
judge = JudgeAgent(bus, config)

ws_clients = []
evolution_running = False
loop = None

PORT = 8000
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


# ─── WebSocket Implementation ─────────────────────

class WebSocketConnection:
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.open = True

    async def send(self, data):
        if not self.open:
            return
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
                opcode = 0x1  # text
            else:
                opcode = 0x2  # binary

            length = len(data)
            header = bytearray()
            header.append(0x80 | opcode)  # FIN + opcode

            if length < 126:
                header.append(length)
            elif length < 65536:
                header.append(126)
                header.extend(struct.pack('>H', length))
            else:
                header.append(127)
                header.extend(struct.pack('>Q', length))

            self.writer.write(bytes(header) + data)
            await self.writer.drain()
        except Exception:
            self.open = False

    async def recv(self):
        try:
            first_byte = await self.reader.readexactly(1)
            second_byte = await self.reader.readexactly(1)

            opcode = first_byte[0] & 0x0F
            masked = second_byte[0] & 0x80
            length = second_byte[0] & 0x7F

            if length == 126:
                length = struct.unpack('>H', await self.reader.readexactly(2))[0]
            elif length == 127:
                length = struct.unpack('>Q', await self.reader.readexactly(8))[0]

            if masked:
                mask = await self.reader.readexactly(4)
                data = bytearray(await self.reader.readexactly(length))
                for i in range(length):
                    data[i] ^= mask[i % 4]
                data = bytes(data)
            else:
                data = await self.reader.readexactly(length)

            if opcode == 0x8:  # Close
                self.open = False
                return None
            if opcode == 0x9:  # Ping
                await self._send_pong(data)
                return await self.recv()

            return data.decode('utf-8') if opcode == 0x1 else data
        except Exception:
            self.open = False
            return None

    async def _send_pong(self, data):
        header = bytearray([0x8A, len(data)])
        self.writer.write(bytes(header) + data)
        await self.writer.drain()

    async def close(self):
        self.open = False
        try:
            self.writer.close()
        except Exception:
            pass


async def websocket_handshake(reader, writer, headers):
    key = None
    for line in headers:
        if line.lower().startswith('sec-websocket-key:'):
            key = line.split(':', 1)[1].strip()
            break

    if not key:
        return None

    accept = base64.b64encode(
        hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-5AB5DCFBC11E').encode()).digest()
    ).decode()

    response = (
        'HTTP/1.1 101 Switching Protocols\r\n'
        'Upgrade: websocket\r\n'
        'Connection: Upgrade\r\n'
        f'Sec-WebSocket-Accept: {accept}\r\n'
        '\r\n'
    )
    writer.write(response.encode())
    await writer.drain()

    return WebSocketConnection(reader, writer)


# ─── Broadcast ─────────────────────────────────────

async def broadcast_ws(event, data):
    message = json.dumps({"event": event, "data": data, "timestamp": time.time()})
    dead = []
    for ws in ws_clients:
        try:
            await ws.send(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        ws_clients.remove(ws)


# Wire up A2A bus
async def _a2a_to_ws(message):
    await broadcast_ws("a2a_message", message.to_dict())

bus.subscribe_all(_a2a_to_ws)

async def _evolution_event(event_type, data):
    await broadcast_ws(event_type, data)

engine.on_event(_evolution_event)


# ─── Evolution Logic ───────────────────────────────

async def run_evolution_loop(generations):
    global evolution_running
    evolution_running = True

    engine.initialize_population()
    await broadcast_ws("population_initialized", {
        "population": [s.to_dict() for s in engine.population],
        "stats": engine.get_population_stats(),
    })

    for gen in range(generations):
        if not evolution_running:
            break

        market_data = await okx_client.get_market_data()
        funding = await okx_client.get_funding_rate()
        liquidity = await okx_client.get_cross_chain_liquidity()
        market_data["funding_detail"] = funding
        market_data["cross_chain"] = liquidity

        await broadcast_ws("market_data", market_data)

        snapshot = await engine.run_generation(
            predictor_fn=predictor.generate_population,
            executor_fn=executor.execute_strategies,
            judge_fn=judge.evaluate_population,
            market_data=market_data,
        )

        await broadcast_ws("generation_result", {
            "snapshot": snapshot.to_dict(),
            "population": [s.to_dict() for s in engine.population],
            "stats": engine.get_population_stats(),
            "agents": {
                "predictor": predictor.get_status(),
                "executor": executor.get_status(),
                "judge": judge.get_status(),
            },
        })

        await asyncio.sleep(1.5)

    await broadcast_ws("evolution_complete", {
        "total_generations": engine.generation,
        "final_stats": engine.get_population_stats(),
        "history": [h.to_dict() for h in engine.history],
    })
    evolution_running = False


async def step_evolution():
    if not engine.population:
        engine.initialize_population()
        await broadcast_ws("population_initialized", {
            "population": [s.to_dict() for s in engine.population],
        })

    market_data = await okx_client.get_market_data()
    snapshot = await engine.run_generation(
        predictor_fn=predictor.generate_population,
        executor_fn=executor.execute_strategies,
        judge_fn=judge.evaluate_population,
        market_data=market_data,
    )
    await broadcast_ws("generation_result", {
        "snapshot": snapshot.to_dict(),
        "population": [s.to_dict() for s in engine.population],
        "stats": engine.get_population_stats(),
    })


async def handle_ws_command(ws, msg):
    global evolution_running
    cmd = msg.get("command")

    if cmd == "start_evolution":
        if not evolution_running:
            asyncio.ensure_future(run_evolution_loop(msg.get("generations", 15)))
    elif cmd == "stop_evolution":
        evolution_running = False
        await broadcast_ws("evolution_stopped", {"generation": engine.generation})
    elif cmd == "step_evolution":
        await step_evolution()
    elif cmd == "reset":
        evolution_running = False
        engine.population = []
        engine.generation = 0
        engine.history = []
        judge.fitness_history = []
        judge.safe_mode_active = False
        judge.consecutive_declines = 0
        await broadcast_ws("reset", {"status": "ok"})
    elif cmd == "get_stats":
        await ws.send(json.dumps({
            "event": "stats",
            "data": engine.get_population_stats(),
            "timestamp": time.time(),
        }))
    elif cmd == "get_market":
        market = await okx_client.get_market_data()
        await ws.send(json.dumps({
            "event": "market_data",
            "data": market,
            "timestamp": time.time(),
        }))


# ─── HTTP + WS Server ─────────────────────────────

MIME_TYPES = {
    '.html': 'text/html',
    '.css': 'text/css',
    '.js': 'application/javascript',
    '.json': 'application/json',
    '.png': 'image/png',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
}


def get_api_response(path):
    if path == '/api/status':
        return json.dumps({
            "status": "running",
            "version": "1.0.0",
            "demo_mode": config.DEMO_MODE,
            "evolution": engine.get_population_stats(),
            "agents": {
                "predictor": predictor.get_status(),
                "executor": executor.get_status(),
                "judge": judge.get_status(),
            },
        })
    elif path == '/api/population':
        return json.dumps({
            "population": [s.to_dict() for s in engine.population],
            "stats": engine.get_population_stats(),
        })
    elif path == '/api/history':
        return json.dumps({
            "history": [h.to_dict() for h in engine.history],
        })
    elif path == '/api/messages':
        return json.dumps({
            "messages": [m.to_dict() for m in bus.get_messages(limit=50)],
        })
    return None


async def handle_client(reader, writer):
    try:
        request_line = await asyncio.wait_for(reader.readline(), timeout=10)
        if not request_line:
            writer.close()
            return

        request_text = request_line.decode('utf-8', errors='replace').strip()
        parts = request_text.split(' ')
        if len(parts) < 2:
            writer.close()
            return

        method, path = parts[0], parts[1]

        # Read headers
        headers = []
        while True:
            line = await asyncio.wait_for(reader.readline(), timeout=5)
            line_str = line.decode('utf-8', errors='replace').strip()
            if not line_str:
                break
            headers.append(line_str)

        # Check for WebSocket upgrade
        is_ws = any('upgrade: websocket' in h.lower() for h in headers)

        if is_ws and path == '/ws':
            ws = await websocket_handshake(reader, writer, headers)
            if ws:
                ws_clients.append(ws)
                # Send init
                await ws.send(json.dumps({
                    "event": "init",
                    "data": {
                        "population": [s.to_dict() for s in engine.population],
                        "stats": engine.get_population_stats(),
                        "history": [h.to_dict() for h in engine.history],
                        "agents": {
                            "predictor": predictor.get_status(),
                            "executor": executor.get_status(),
                            "judge": judge.get_status(),
                        },
                        "config": {
                            "population_size": config.POPULATION_SIZE,
                            "mutation_rate": config.MUTATION_RATE,
                            "selection_pressure": config.SELECTION_PRESSURE,
                            "demo_mode": config.DEMO_MODE,
                        },
                    },
                    "timestamp": time.time(),
                }))

                while ws.open:
                    data = await ws.recv()
                    if data is None:
                        break
                    try:
                        msg = json.loads(data)
                        await handle_ws_command(ws, msg)
                    except json.JSONDecodeError:
                        pass

                if ws in ws_clients:
                    ws_clients.remove(ws)
            return

        # API routes
        if path.startswith('/api/'):
            response_body = get_api_response(path)
            if response_body:
                body = response_body.encode('utf-8')
                response = (
                    f'HTTP/1.1 200 OK\r\n'
                    f'Content-Type: application/json\r\n'
                    f'Content-Length: {len(body)}\r\n'
                    f'Access-Control-Allow-Origin: *\r\n'
                    f'\r\n'
                ).encode() + body
                writer.write(response)
                await writer.drain()
                writer.close()
                return

        # Static file serving
        if path == '/':
            path = '/static/index.html'
        elif not path.startswith('/static/'):
            path = '/static' + path

        file_path = os.path.join(os.path.dirname(__file__), path.lstrip('/'))

        if os.path.isfile(file_path):
            ext = os.path.splitext(file_path)[1]
            content_type = MIME_TYPES.get(ext, 'application/octet-stream')

            with open(file_path, 'rb') as f:
                body = f.read()

            response = (
                f'HTTP/1.1 200 OK\r\n'
                f'Content-Type: {content_type}\r\n'
                f'Content-Length: {len(body)}\r\n'
                f'\r\n'
            ).encode() + body
        else:
            body = b'404 Not Found'
            response = (
                f'HTTP/1.1 404 Not Found\r\n'
                f'Content-Type: text/plain\r\n'
                f'Content-Length: {len(body)}\r\n'
                f'\r\n'
            ).encode() + body

        writer.write(response)
        await writer.drain()
        writer.close()

    except Exception as e:
        try:
            writer.close()
        except Exception:
            pass


async def main():
    server = await asyncio.start_server(handle_client, '0.0.0.0', PORT)
    print(f'GeneFi server running on http://0.0.0.0:{PORT}')
    print(f'GeneFi - Gene + DeFi Evolution Engine v1.0.0 - Demo Mode: {config.DEMO_MODE}')
    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    asyncio.run(main())
